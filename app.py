import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET

# --- 1. DE SLIMME REKENMOTOR ---
def parse_xaf_auditfile(file_content):
    try:
        root = ET.fromstring(file_content)
        for el in root.iter():
            if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
        data = []
        # Brede zoekactie naar transactieregels in Snelstart XML
        lines = root.findall('.//trLine') + root.findall('.//transaction') + root.findall('.//journalTransaction')
        for line in lines:
            try:
                desc_el = line.find('description') or line.find('.//desc')
                desc = desc_el.text if (desc_el is not None and desc_el.text) else ""
                amnt_el = line.find('amnt') or line.find('.//amount') or line.find('amntTp')
                amnt = abs(float(amnt_el.text)) if (amnt_el is not None and amnt_el.text) else 0.0
                if amnt > 0: # Alleen regels met bedragen meenemen
                    data.append({'omschrijving': desc, 'bedrag': amnt})
            except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame(columns=['omschrijving', 'bedrag'])

def scan_boekhouding(df):
    results = []
    # Uitgebreide lijst met zoektermen voor Nederlandse subsidies
    keywords = {
        'MIA/EIA (Milieu/Energie)': ['elektr', 'zonnepan', 'laadpaal', 'accu', 'warmtepomp', 'isolatie', 'led', 'bus', 'truck'],
        'KIA (Kleinschaligheidsaftrek)': ['machine', 'inventaris', 'computer', 'laptop', 'gereedschap', 'installatie'],
        'VAMIL': ['milieu', 'innovatie', 'duurzaam']
    }
    for _, row in df.iterrows():
        omschr = str(row.get('omschrijving', '')).lower()
        bedrag = row.get('bedrag', 0)
        for cat, terms in keywords.items():
            if any(term in omschr for term in terms):
                results.append({
                    "Categorie": cat,
                    "Investering": row.get('omschrijving'),
                    "Bedrag": f"€ {bedrag:,.2f}",
                    "Potentieel Voordeel": f"€ {bedrag * 0.12:,.2f}" # Gemiddeld netto voordeel
                })
    return results

# --- 2. DE STRAKKE UI ---
st.set_page_config(page_title="Compliance Sencil | Enterprise Hub", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #080a0f; color: #e0e0e0; }
    .stMetric { 
        background-color: #11151c; 
        padding: 20px; 
        border-radius: 15px; 
        border: 1px solid #222;
        border-top: 4px solid #00ff41;
        box-shadow: 0 4px 15px rgba(0,255,65,0.1);
    }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-family: 'Courier New', monospace; font-weight: bold; }
    .stTable { background-color: #11151c; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Enterprise Hub")
st.write("---")

uploaded_file = st.file_uploader("📂 Sleep hier je Snelstart Auditfile (.xaf)", type=["xaf"])

if uploaded_file:
    df = parse_xaf_auditfile(uploaded_file.getvalue())
    if not df.empty:
        hits = scan_boekhouding(df)
        
        # Dashboard Header
        c1, c2, c3 = st.columns(3)
        total_potential = sum([float(h['Potentieel Voordeel'].replace('€ ','').replace(',','')) for h in hits]) if hits else 0
        
        c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {total_potential:,.2f}")
        c2.metric("GEDETECTEERDE KANSEN", len(hits))
        c3.metric("ANALYSE STATUS", "OPTIMAAL")
        
        st.write("### 🔍 Gedetecteerde Investeringen & Subsidies")
        if hits:
            st.table(pd.DataFrame(hits))
        else:
            st.warning("Geen investeringen herkend. Tip: Controleer of de Auditfile omschrijvingen bevat zoals 'Elektrische bus' of 'Zonnepanelen'.")
    else:
        st.error("Bestand kon niet worden gelezen als Snelstart Auditfile.")
