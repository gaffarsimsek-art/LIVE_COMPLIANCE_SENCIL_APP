import streamlit as st
import pandas as pd
import re

def parse_xaf_activa_only(file_content):
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
                
                # STRENG FILTER: Alleen Materiële Vaste Activa (vaak rekeningen 0-999)
                # We negeren alles boven de 1000 (Voorraden, Vorderingen, Kosten, Omzet)
                if acc_val.isdigit() and int(acc_val) < 1000:
                    
                    # Alleen DEBET boekingen (toename van bezit/activatie)
                    if tp.group(1) == 'D':
                        try:
                            val = float(amnt.group(1))
                            description = desc.group(1) if desc else "Geen omschrijving"
                            
                            # Negeer expliciet afschrijvingen en beginbalans
                            clean_desc = description.lower()
                            if not any(x in clean_desc for x in ['afschrijving', 'afschr', 'beginbalans', 'openingsbalans']):
                                if val >= 450: # KIA drempel per bedrijfsmiddel
                                    data.append({
                                        'rekening': acc_val,
                                        'omschrijving': description,
                                        'bedrag': val
                                    })
                        except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def scan_activa_subsidies(df):
    results = []
    if df.empty: return results
    
    # Verwijder dubbelingen
    df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
    
    for _, row in df.iterrows():
        d = str(row['omschrijving']).lower()
        b = row['bedrag']
        
        # Bepaal subsidietype
        if any(x in d for x in ['elek', 'zon', 'laad', 'warmte', 'accu']):
            perc = 0.135
            cat = "MIA/EIA (Milieu/Energie)"
        else:
            perc = 0.28
            cat = "KIA (Kleinschaligheid)"
            
        results.append({
            "Categorie": cat,
            "Activa Post": row['omschrijving'],
            "Investering (Ex. BTW)": b,
            "Fiscaal Voordeel": b * perc
        })
    return results

# --- UI ---
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.markdown("<style>.stApp { background-color: #0b0e14; color: white; }</style>", unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Activa Analyse")
st.info("Deze scan kijkt uitsluitend naar nieuwe investeringen op de balans (Materiële Vaste Activa).")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df = parse_xaf_activa_only(file.getvalue())
    if not df.empty:
        hits = scan_activa_subsidies(df)
        
        c1, c2, c3 = st.columns(3)
        totaal_v = sum([h['Fiscaal Voordeel'] for h in hits])
        c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {totaal_v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        c2.metric("NIEUWE ACTIVA", len(hits))
        c3.metric("FOCUS", "BALANS / MATERIEEL")
        
        if hits:
            st.write("### 🔍 Geactiveerde Investeringen 2024")
            st.table(pd.DataFrame(hits).style.format({
                'Investering (Ex. BTW)': '€ {:,.2f}',
                'Fiscaal Voordeel': '€ {:,.2f}'
            }))
        else:
            st.warning("Geen nieuwe geactiveerde investeringen boven € 450 gevonden op de balans.")
    else:
        st.error("Geen activa-transacties gevonden.")
