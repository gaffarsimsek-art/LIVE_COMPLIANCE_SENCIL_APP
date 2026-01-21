import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET

# 1. PARSER VOOR DE DATA
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
                amnt_el = line.find('amnt')
                amnt = float(amnt_el.text) if (amnt_el is not None and amnt_el.text) else 0.0
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
        
        # Investerings-radar: Rekeningen < 1000 (Balans) of trefwoorden
        is_invest = (acc.isdigit() and 0 < int(acc) < 1000) or any(t in desc for t in ['hp', 'computer', 'laptop', 'machine'])
        is_green = any(t in desc for t in ['elektr', 'zonne', 'laad', 'warmtepomp'])

        if is_green and bedrag > 2000:
            results.append({"Type": "MIA/EIA Potentieel", "Item": row['omschrijving'], "Bedrag": bedrag, "Fiscaal Voordeel": bedrag * 0.135})
        elif is_invest and bedrag >= 450:
            results.append({"Type": "KIA Potentieel", "Item": row['omschrijving'], "Bedrag": bedrag, "Fiscaal Voordeel": bedrag * 0.28})
    return results

# 2. INTERFACE (NU MET VEILIGE KLEUREN)
st.set_page_config(page_title="Compliance Sencil", layout="wide")

# CSS voor een strakke look maar mét zichtbare tekst
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3, p { color: white !important; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Enterprise Hub")
st.write("Analyseer uw Snelstart Auditfile op fiscale kansen.")

uploaded_file = st.file_uploader("Upload hier het .xaf bestand", type=["xaf"])

if uploaded_file:
    with st.spinner('Bezig met diepte-analyse...'):
        df = deep_parse_xaf(uploaded_file.getvalue())
        
        if not df.empty:
            hits = scan_voor_subsidies(df)
            
            # Dashboard
            c1, c2, c3 = st.columns(3)
            totaal = sum([h['Fiscaal Voordeel'] for h in hits]) if hits else 0
            
            c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {totaal:,.2f}")
            c2.metric("GEDETECTEERDE KANSEN", len(hits))
            c3.metric("ANALYSE STATUS", "OPTIMAAL")
            
            if hits:
                st.write("### Gevonden Investeringen")
                st.dataframe(pd.DataFrame(hits), use_container_width=True)
            else:
                st.info("Geen investeringen boven de €450 herkend.")
        else:
            st.error("Het bestand bevat geen leesbare transacties.")
else:
    st.info("Klaar voor analyse. Sleep een Auditfile in het vak hierboven.")
