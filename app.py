import streamlit as st
import pandas as pd
import re

# 1. HULPFUNCTIES
def extract_kenteken(text):
    patroon = r'\b([A-Z0-9]{2}-?[A-Z0-9]{2}-?[A-Z0-9]{2}|[A-Z]{1}-?\d{3}-?[A-Z]{2})\b'
    match = re.search(patroon, str(text).upper())
    return match.group(0) if match else None

def parse_xaf_fiscal_expert(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        data = []
        
        # STRENGE BLACKLIST (Geen ruis, lease of verzekering)
        blacklist = [
            'vwpfs', 'mercedes-benz fin', 'financial', 'lease', 'insurance', 
            'verzekering', 'wa casco', 'premie', 'corr', 'afschr', 'termijn', 
            'rente', 'beginbalans', 'opening', 'vpb', 'btw'
        ]

        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            tp = re.search(r'<amntTp>(.*?)</amntTp>', line)
            
            if acc and amnt and tp:
                acc_id = acc.group(1)
                description = desc.group(1) if desc else ""
                clean_desc = description.lower()
                
                # Filter: Alleen Activa-zijde (Materiële Vaste Activa < 500)
                if acc_id.isdigit() and int(acc_id) < 500:
                    if any(x in clean_desc for x in blacklist):
                        continue

                    # Alleen inkoop (Debet)
                    if tp.group(1) == 'D':
                        try:
                            val = float(amnt.group(1).replace(',', '.'))
                            if val >= 450:
                                data.append({'rekening': acc_id, 'omschrijving': description, 'bedrag': val})
                        except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# 2. UI DESIGN
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.title("🛡️ Compliance Sencil | Fiscale Audit")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df = parse_xaf_fiscal_expert(file.getvalue())
    if not df.empty:
        df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
        
        st.write("### 🔍 Analyse van Materiële Activa")
        
        items = []
        for _, row in df.iterrows():
            d = row['omschrijving'].lower()
            b = row['bedrag']
            ken = extract_kenteken(row['omschrijving'])
            
            # --- SUBSIDIE CLASSIFICATIE ---
            subsidie = "KIA" # Standaard
            toelichting = "Kleinschaligheidsinvesteringsaftrek (algemeen)"
            
            # Check voor Duurzaamheid (MIA/EIA)
            is_elek = any(x in d for x in ['elektr', 'taycan', 'ev ', 'eqs', 'tesla', 'laadpaal'])
            is_energie = any(x in d for x in ['zonne', 'led', 'warmtepomp', 'isolatie'])
            
            if is_elek:
                subsidie = "MIA / Vamil"
                toelichting = "Milieu-investering (Elektrisch vervoer)"
            elif is_energie:
                subsidie = "EIA"
                toelichting = "Energie-investering"
            
            # Skip brandstofauto's (Geen KIA/MIA voor personenauto's op brandstof)
            if ken and not is_elek and any(x in d for x in ['mercedes', 'porsche', 'audi', 'bmw']):
                continue

            items.append({
                "Regeling": subsidie,
                "Omschrijving": row['omschrijving'],
                "Investering": b,
                "Fiscaal Voordeel (Indicatie)": b * (0.28 if subsidie == "KIA" else 0.135),
                "Toelichting": toelichting
            })
        
        if items:
            res_df = pd.DataFrame(items)
            st.table(res_df.style.format({'Investering': '€ {:,.2f}', 'Fiscaal Voordeel (Indicatie)': '€ {:,.2f}'}))
            
            totaal_v = sum([h['Fiscaal Voordeel (Indicatie)'] for h in items])
            st.metric("TOTAAL GESCHAT VOORDEEL", f"€ {totaal_v:,.2f}")
        else:
            st.info("Geen subsidiabele activa gevonden na menselijke filtering.")
