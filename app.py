import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET

# 1. DE REKENMOTOR & PARSER
def deep_parse_xaf(file_content):
    try:
        root = ET.fromstring(file_content)
        for el in root.iter():
            if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
        data = []
        for line in root.findall('.//trLine'):
            try:
                acc_id = line.find('accID').text if line.find('accID') is not None else ""
                desc = line.find('description').text if line.find('description') is not None else ""
                amnt = float(line.find('amnt').text) if line.find('amnt') is not None else 0.0
                if amnt != 0:
                    data.append({'rekening': acc_id, 'omschrijving': desc, 'bedrag': abs(amnt)})
            except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def scan_voor_subsidies(df):
    results = []
    if df.empty: return results
    df_unique = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
    for _, row in df_unique.iterrows():
        desc = str(row['omschrijving']).lower()
        acc = str(row['rekening'])
        bedrag = row['bedrag']
        
        # Investerings-radar (Rekeningen onder 1000 of specifieke termen)
        is_invest = (acc.isdigit() and int(acc) < 1000) or any(t in desc for t in ['hp', 'computer', 'laptop', 'machine', 'bus'])
        is_green = any(t in desc for t in ['elektr', 'zonne', 'laad', 'warmtepomp'])

        if is_green and bedrag > 2000:
            results.append({"Type": "MIA/EIA Potentieel", "Item": row['omschrijving'], "Bedrag": bedrag, "Fiscaal Voordeel": bedrag * 0.135})
        elif is_invest and bedrag >= 450:
            results.append({"Type": "KIA Potentieel", "Item": row['omschrijving'], "Bedrag": bedrag, "Fiscaal Voordeel": bedrag * 0.28})
    return results

# 2. DE LOOK & FEEL (HET ZWARTE DASHBOARD)
st.set_page_config(page_title="Compliance Sencil | Enterprise Hub", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #080a0f; color: #e0e0e0; }
    .stMetric { 
        background-color: #11151c; 
        padding: 20px; 
        border-radius: 15px; 
        border-top: 4px solid #00ff41;
        box-shadow: 0 4px 15px rgba(0,255,65,0.1);
    }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-family: 'Courier New', monospace; }
    .stTable { background-color: #11151c; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Enterprise Hub")
st.write("---")

uploaded_file = st.file_uploader("📂 Sleep hier de Auditfile (.xaf) van je klant", type=["xaf"])

if uploaded_file:
    df = deep_parse_xaf(uploaded_file.getvalue())
    if not df.empty:
        hits = scan_voor_subsidies(df)
        
        # Dashboard Cijfers
        c1, c2, c3 = st.columns(3)
        totaal_voordeel = sum([h['Fiscaal Voordeel'] for h in hits]) if hits else 0
        
        c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {totaal_voordeel:,.2f}")
        c2.metric("GEDETECTEERDE KANSEN", len(hits))
        c3.metric("ANALYSE STATUS", "OPTIMAAL")
        
        st.write("### 🔍 Gedetecteerde Investeringen")
        if hits:
            st.table(pd.DataFrame(hits))
        else:
            st.info("Geen investeringen boven de €450 herkend in deze file.")
    else:
        st.error("Bestand kon niet worden gelezen. Controleer of het een Snelstart XAF bestand is.")
else:
    st.info("Upload een bestand om de scan te starten.")
