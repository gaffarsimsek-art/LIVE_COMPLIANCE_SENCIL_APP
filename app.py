import streamlit as st
import pandas as pd
import re

def clean_and_parse_amount(raw_val):
    """Vertaalt elke getalnotatie veilig naar een rekenbaar getal."""
    if not raw_val:
        return 0.0
    # Verwijder spaties en vreemde tekens
    clean_val = raw_val.strip().replace(' ', '')
    
    # Als er zowel een punt als een komma in staat (bijv. 1.652,07)
    if '.' in clean_val and ',' in clean_val:
        clean_val = clean_val.replace('.', '').replace(',', '.')
    # Als er alleen een komma in staat (bijv. 1652,07)
    elif ',' in clean_val:
        clean_val = clean_val.replace(',', '.')
        
    try:
        return abs(float(clean_val))
    except ValueError:
        return 0.0

def parse_xaf_robust(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        
        data = []
        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            
            if acc and amnt:
                acc_id = acc.group(1)
                description = desc.group(1) if desc else ""
                
                # Filter: Alleen Activa rekeningen (< 3000)
                if not (acc_id.isdigit() and int(acc_id) < 3000):
                    continue
                
                # Filter: Geen afschrijvingen of beginbalans
                if any(x in description.lower() for x in ['beginbalans', 'openingsbalans', 'afschrijving']):
                    continue

                # Gebruik de nieuwe robuuste getal-cleaner
                num_val = clean_and_parse_amount(amnt.group(1))
                
                if num_val > 0:
                    data.append({
                        'rekening': acc_id,
                        'omschrijving': description,
                        'bedrag': num_val
                    })
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Fout in verwerking: {e}")
        return pd.DataFrame()

# --- DASHBOARD ---
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: white; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Precision Hub")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df = parse_xaf_robust(file.getvalue())
    if not df.empty:
        # Groepeer om dubbele regels (debet/credit) te filteren
        df_unique = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
        
        hits = []
        for _, row in df_unique.iterrows():
            if row['bedrag'] >= 450:
                perc = 0.135 if any(x in row['omschrijving'].lower() for x in ['elek', 'zon', 'laad']) else 0.28
                hits.append({
                    "Type": "MIA/EIA" if perc == 0.135 else "KIA",
                    "Omschrijving": row['omschrijving'],
                    "Bedrag (Ex. BTW)": row['bedrag'],
                    "Fiscaal Voordeel": row['bedrag'] * perc
                })
        
        if hits:
            res_df = pd.DataFrame(hits)
            c1, c2 = st.columns(2)
