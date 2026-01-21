import streamlit as st
import pandas as pd
import re

def extract_kenteken(text):
    patroon = r'\b([A-Z0-9]{2}-?[A-Z0-9]{2}-?[A-Z0-9]{2}|[A-Z]{1}-?\d{3}-?[A-Z]{2})\b'
    match = re.search(patroon, text.upper())
    return match.group(0) if match else None

def parse_xaf_final_logic(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        
        data = []
        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            tp = re.search(r'<amntTp>(.*?)</amntTp>', line)
            
            if acc and amnt and tp:
                description = desc.group(1) if desc else ""
                clean_desc = description.lower()
                
                # --- STRENG EXCLUSIE FILTER ---
                uitsluit_termen = [
                    'vwpfs', 'mercedes-benz fin', 'financial services', 'lease', 
                    'insurance', 'verzekering', 'wa casco', 'premie', 
                    'corr', 'beginbalans', 'afschr', 'rente', 'termijn'
                ]
                
                if any(x in clean_desc for x in uitsluit_termen):
                    continue

                # Alleen Activa rekeningen (< 1000) en Debet (inkoop)
                if acc.group(1).isdigit() and int(acc.group(1)) < 1000 and tp.group(1) == 'D':
                    val = float(amnt.group(1).replace(',', '.'))
                    if val >= 450:
                        data.append({'rekening': acc.group(1), 'omschrijving': description, 'bedrag': val})
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# --- UI ---
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.title("🛡️ Compliance Sencil | Precision Activa Scan")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df = parse_xaf_final_logic(file.getvalue())
    
    if not df.empty:
        # Groepeer om dubbele boekingen te voorkomen
        df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
        
        st.write("### 🔍 Gevonden Materiële Activa")
        
        results = []
        for _, row in df.iterrows():
            ken = extract_kenteken(row['omschrijving'])
            results.append({
                "Activa": row['omschrijving'],
                "Bedrag": row['bedrag'],
                "Kenteken": ken if ken else "Geen voertuig",
                "Status": "Klaar voor RDW check" if ken else "Inventaris"
            })
        
        res_df = pd.DataFrame(results)
        st.table(res_df.style.format({'Bedrag': '€ {:,.2f}'}))

        # RDW CHECK BUTTON
        if st.button("🚀 Start RDW Kenteken & Brandstof Analyse"):
            st.write("---")
            st.subheader("RDW Analyse Resultaten")
            
            final_hits = []
            for item in results:
                desc = item['Activa'].lower()
                bed
