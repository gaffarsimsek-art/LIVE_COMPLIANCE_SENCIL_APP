import streamlit as st
import pandas as pd
import re

def parse_xaf_human_logic(file_content):
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
                clean_desc = description.lower()
                
                # --- MENSELIJK FILTER (Uitsluiten wat geen investering is) ---
                uitsluit_termen = [
                    'corr', 'correctie', 'beginbalans', 'openingsbalans', 
                    'insurance', 'verzekering', 'wa casco', 'premie',
                    'lease', 'financial', 'vwpfs', 'mercedes-benz fin',
                    'afschrijving', 'afschr', 'rente', 'termijn'
                ]
                
                if any(x in clean_desc for x in uitsluit_termen):
                    continue

                # Alleen Activa rekeningen (< 1000) en Debet (inkoop/toename)
                if acc_val.isdigit() and int(acc_val) < 1000 and tp.group(1) == 'D':
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

def scan_kansen(df):
    results = []
    if df.empty: return results
    
    # Voorkom dubbele regels
    df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
    
    for _, row in df.iterrows():
        d = str(row['omschrijving']).lower()
        b = row['bedrag']
        
        # Alleen echte activa-items herkennen
        is_pc = any(x in d for x in ['hp', 'computer', 'laptop', 'macbook', 'pc'])
        is_groen = any(x in d for x in ['elek', 'zon', 'laad', 'accu'])
        
        if is_pc or is_groen or b > 1000: # Alles boven de 1000 op de balans is vaak een machine/auto
            cat = "MIA/EIA" if is_groen else "KIA"
            perc = 0.135 if is_groen else 0.28
            
            results.append({
                "Categorie": cat,
                "Investering": row['omschrijving'],
                "Bedrag (Ex. BTW)": b,
                "Fiscaal Voordeel": b * perc
            })
    return results

# --- UI ---
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.markdown("<style>.stApp { background-color: #0b0e14; color: white; }</style>", unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Human Intelligence")
st.write("Analyseert alleen materiële vaste activa. Correcties en verzekeringen worden automatisch gefilterd.")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df = parse_xaf_human_logic(file.getvalue())
    if not df.empty:
        hits = scan_kansen(df)
        
        c1, c2, c3 = st.columns(3)
        totaal_v = sum([h['Fiscaal Voordeel'] for h in hits])
        c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {totaal_v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        c2.metric("ECHTE INVESTERINGEN", len(hits))
        c3.metric("LOGICA", "MENSELIJK FILTER")
        
        if hits:
            st.table(pd.DataFrame(hits).style.format({
                'Bedrag (Ex. BTW)': '€ {:,.2f}',
                'Fiscaal Voordeel': '€ {:,.2f}'
            }))
        else:
            st.info("Geen nieuwe investeringen gevonden. (Correcties en premies succesvol genegeerd)")
