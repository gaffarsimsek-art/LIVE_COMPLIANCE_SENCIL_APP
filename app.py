import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET

# --- 1. REKENMOTOR (Direct in app.py voor stabiliteit) ---
def parse_xaf_auditfile(file_content):
    try:
        root = ET.fromstring(file_content)
        for el in root.iter():
            if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
        
        data = []
        # Snelstart specifieke tags: trLine of transaction
        lines = root.findall('.//trLine') + root.findall('.//transaction')
        
        for line in lines:
            try:
                desc_el = line.find('description')
                desc = desc_el.text if (desc_el is not None and desc_el.text) else "Omschrijving mist"
                
                amnt_el = line.find('amnt') or line.find('amount')
                amnt = float(amnt_el.text) if (amnt_el is not None and amnt_el.text) else 0.0
                
                data.append({'omschrijving': desc, 'bedrag': amnt})
            except:
                continue
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame(columns=['omschrijving', 'bedrag'])

def scan_boekhouding(df):
    results = []
    if df.empty: return results
    for _, row in df.iterrows():
        omschr = str(row.get('omschrijving', '')).lower()
        bedrag = row.get('bedrag', 0)
        # Zoek naar MIA/EIA hints
        if any(keyword in omschr for keyword in ['elektr', 'zonnepaneel', 'laadpaal', 'warmtepomp']):
            results.append({
                "Type": "Fiscaal Voordeel (MIA/EIA)",
                "Bedrag": bedrag * 0.135, # Gemiddeld netto voordeel
                "Check": f"Gevonden op basis van: '{omschr}'"
            })
    return results

# --- 2. DASHBOARD INTERFACE ---
st.set_page_config(page_title="Compliance Sencil | Enterprise Hub", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border-left: 5px solid #00ff00; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Enterprise Hub")

uploaded_file = st.file_uploader("Upload Snelstart Auditfile (.xaf)", type=["xaf"])

if uploaded_file is not None:
    try:
        content = uploaded_file.getvalue()
        df = parse_xaf_auditfile(content)
        
        if not df.empty:
            results = scan_boekhouding(df)
            total_voordeel = sum([r['Bedrag'] for r in results])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {total_voordeel:,.2f}")
            col2.metric("SCAN STATUS", "100% Voltooid")
            col3.metric("ENTITEIT", "Snelstart Administratie")
            
            if results:
                st.table(pd.DataFrame(results))
            else:
                st.info("Scan voltooid: Geen directe MIA/EIA kansen gevonden in deze file.")
        else:
            st.error("De Auditfile bevat geen leesbare transactiegegevens.")
    except Exception as e:
        st.error(f"Systeemfout: {e}")
