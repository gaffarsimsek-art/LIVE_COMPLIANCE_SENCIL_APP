import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET

def deep_parse_xaf(file_content):
    try:
        root = ET.fromstring(file_content)
        for el in root.iter():
            if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
            
        data = []
        # We scannen alle transactielijnen
        for line in root.findall('.//trLine'):
            try:
                acc_id = line.find('accID').text if line.find('accID') is not None else ""
                desc = line.find('description').text if line.find('description') is not None else ""
                amnt = float(line.find('amnt').text) if line.find('amnt') is not None else 0.0
                
                # Alleen relevante regels (geen 0-bedragen)
                if amnt != 0:
                    data.append({
                        'rekening': acc_id,
                        'omschrijving': desc,
                        'bedrag': abs(amnt)
                    })
            except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def scan_voor_subsidies(df):
    results = []
    if df.empty: return results

    for _, row in df.iterrows():
        desc = str(row['omschrijving']).lower()
        acc = str(row['rekening'])
        bedrag = row['bedrag']

        # 1. SCAN OP REKENINGNUMMER (De 'Investerings-radar')
        # Rekeningen onder de 1000 zijn in NL bijna altijd Balans/Investeringen
        is_investering_account = acc.isdigit() and int(acc) < 1000 and int(acc) > 0
        
        # 2. SCAN OP TREFWOORDEN
        subsidie_terms = ['elektr', 'zonne', 'laad', 'warmtepomp', 'accu', 'isolatie', 'led']
        kia_terms = ['hp', 'computer', 'laptop', 'pc', 'machine', 'inventaris', 'gereedschap', 'meubilair', 'inrichting']

        # Detectie logica
        if any(t in desc for t in subsidie_terms):
            results.append({"Type": "MIA/EIA Potentieel", "Item": row['omschrijving'], "Bedrag": bedrag, "Voordeel": bedrag * 0.12})
        elif is_investering_account or any(t in desc for t in kia_terms):
            if bedrag >= 450: # Fiscale ondergrens voor investeringen
                results.append({"Type": "KIA Potentieel", "Item": row['omschrijving'], "Bedrag": bedrag, "Voordeel": bedrag * 0.28})

    return results

# --- UI GEDEELTE ---
st.set_page_config(page_title="Compliance Sencil | Enterprise Hub", layout="wide")
st.markdown("<style>.stMetric { background-color: #11151c; border-top: 4px solid #00ff41; color: white; }</style>", unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Universele Scanner")

uploaded_file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if uploaded_file:
    df = deep_parse_xaf(uploaded_file.getvalue())
    if not df.empty:
        hits = scan_voor_subsidies(df)
        
        c1, c2, c3 = st.columns(3)
        totaal = sum([h['Voordeel'] for h in hits])
        c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {totaal:,.2f}")
        c2.metric("GEDETECTEERDE ITEMS", len(hits))
        c3.metric("SCORE", "OPTIMAAL")
        
        if hits:
            st.table(pd.DataFrame(hits))
        else:
            st.info("Geen investeringen boven de €450 gevonden.")
