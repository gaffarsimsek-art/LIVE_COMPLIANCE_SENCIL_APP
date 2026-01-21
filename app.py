import streamlit as st
import pandas as pd
import re

# 1. PARSER (Nu met extra checks voor Snelstart-tags)
def parse_xaf_safe(file_content):
    try:
        # Decodeer de file
        text = file_content.decode('iso-8859-1', errors='ignore')
        
        # Zoek alle transactieregels
        lines = re.findall(r'<trLine>.*?</trLine>', text, re.DOTALL)
        
        data = []
        for line in lines:
            # We zoeken naar accID, amnt en description (Snelstart gebruikt de lange naam)
            acc_match = re.search(r'<accID>(.*?)</accID>', line)
            desc_match = re.search(r'<description>(.*?)</description>', line) or re.search(r'<desc>(.*?)</desc>', line)
            amnt_match = re.search(r'<amnt>(.*?)</amnt>', line)
            
            if acc_match and amnt_match:
                acc = acc_match.group(1)
                desc = desc_match.group(1) if desc_match else "Geen omschrijving"
                try:
                    amnt = abs(float(amnt_match.group(1)))
                except:
                    amnt = 0.0
                
                if amnt > 0:
                    data.append({'rekening': acc, 'omschrijving': desc, 'bedrag': amnt})
        
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Fout bij inlezen: {e}")
        return pd.DataFrame()

def scan_boekhouding(df):
    results = []
    if df.empty: return results
    
    # Verwijder dubbele boekingen (Debet/Credit)
    df_unique = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
    
    for _, row in df_unique.iterrows():
        d = str(row['omschrijving']).lower()
        a = str(row['rekening'])
        b = row['bedrag']
        
        # Specifieke checks voor Ave Export & Universeel
        # 1. MIA/EIA (Elektrisch, Zonne, etc.)
        if any(x in d for x in ['elek', 'zon', 'laad', 'accu', 'warmte']):
            results.append({"Type": "MIA/EIA Potentieel", "Item": row['omschrijving'], "Investering": b, "Voordeel": b * 0.135})
        
        # 2. KIA (Investeringen op balansrekeningen < 1000 of computers)
        elif (a.isdigit() and int(a) < 1000) or any(x in d for x in ['hp ', 'comp', 'pc', 'laptop', 'apple', 'macbook']):
            if b >= 450:
                results.append({"Type": "KIA Potentieel", "Item": row['omschrijving'], "Investering": b, "Voordeel": b * 0.28})
                
    return results

# 2. DE INTERFACE (Zwart met Contrast)
st.set_page_config(page_title="Compliance Sencil", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: white; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-weight: bold; }
    h1, h2, h3 { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Enterprise Hub")

uploaded_file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if uploaded_file:
    # Voorkom crash door try/except om de hele flow
    try:
        df = parse_xaf_safe(uploaded_file.getvalue())
        
        if not df.empty:
            hits = scan_boekhouding(df)
            
            c1, c2, c3 = st.columns
