import streamlit as st
import pandas as pd
import re

def parse_xaf_strict_activa(file_content):
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
                acc_val = acc.group(1)
                description = desc.group(1) if desc else ""
                
                # --- STRENG FILTER ---
                # 1. Alleen Balans/Activa (rekening < 1000)
                if not (acc_val.isdigit() and int(acc_val) < 1000):
                    continue
                
                # 2. Sluit Lease en Kosten uit (geen VWPFS of Mercedes Financial)
                clean_desc = description.lower()
                exclude_terms = [
                    'financial', 'lease', 'vwpfs', 'mercedes-benz fin', 
                    'termijn', 'afschrijving', 'afschr', 'beginbalans', 'rente'
                ]
                if any(x in clean_desc for x in exclude_terms):
                    continue

                # 3. Alleen Debet (toename activa)
                if tp.group(1) == 'D':
                    try:
                        val = float(amnt.group(1).replace(',', '.'))
                        if val >= 450:
                            data.append({
                                'rekening': acc_val,
                                'omschrijving': description,
                                'bedrag': val
                            })
                    except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def scan_activa(df):
    results = []
    if df.empty: return results
    
    # Verwijder dubbelingen
    df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
    
    for _, row in df.iterrows():
        d = str(row['omschrijving']).lower()
        b = row['bedrag']
        
        # Check voor MIA/EIA (alleen als het echt om een groene investering gaat)
        if any(x in d for x in ['elek', 'zon', 'laad', 'accu']):
            perc = 0.135
            cat = "MIA/EIA (Duurzaam)"
        else:
            perc = 0.28
            cat = "KIA (Kleinschaligheid)"
            
        results.append({
            "Categorie": cat,
            "Activa Post": row['omschrijving'],
            "Bedrag (Ex. BTW)": b,
            "Fiscaal Voordeel": b * perc
        })
    return results

# --- UI ---
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.markdown("<style>.stApp { background-color: #0b0e14; color: white; }</style>", unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Activa Filter")
st.write("Gefilterd op Materiële Vaste Activa. Lease- en afschrijvingskosten zijn uitgesloten.")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df = parse_xaf_strict_activa(file.getvalue())
    if not df.empty:
        hits = scan_activa(df)
        
        c1, c2, c3 = st.columns(3)
        totaal_v = sum([h['Fiscaal Voordeel'] for h in hits])
        c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {totaal_v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        c2.metric("NIEUWE INVESTERINGEN", len(hits))
        c3.metric("FILTER STATUS", "LEASE GEFILTERD")
        
        if hits:
            st.table(pd.DataFrame(hits).style.format({
                'Bedrag (Ex. BTW)': '€ {:,.2f}',
                'Fiscaal Voordeel': '€ {:,.2f}'
            }))
        else:
            st.info("Geen nieuwe activa-investeringen gevonden na filtering van lease en afschrijvingen.")
