import streamlit as st
import pandas as pd
import re

# --- 1. AI LOGIC ENGINE ---
def ai_analyze_transaction(desc, amount, account):
    d = str(desc).lower()
    a = str(account)
    
    # AI Scorecard
    score_kia = 0
    score_mia_eia = 0
    is_excluded = False

    # Uitsluitingsfactoren (De "Menselijke" check)
    if any(x in d for x in ['lease', 'financial', 'insurance', 'verzekering', 'premie', 'corr', 'afschr', 'rente', 'vwpfs', 'mercedes-benz fin']):
        is_excluded = True
        return None, 0, "Exploitatiekosten of correctie"

    # Positieve signalen voor KIA (Hardware, Inventaris)
    if any(x in d for x in ['hp ', 'computer', 'laptop', 'macbook', 'pc', 'monitor', 'meubilair', 'kast']):
        score_kia += 10
    
    # Positieve signalen voor MIA/EIA (Duurzaamheid)
    if any(x in d for x in ['elektr', 'taycan', 'ev ', 'eqs', 'tesla', 'laadpaal', 'zonne', 'led', 'warmtepomp']):
        score_mia_eia += 10

    # Fiscale beslissing
    if score_mia_eia >= 10:
        return "MIA / EIA", 0.135, "AI-Detectie: Duurzame investering"
    elif score_kia >= 10 or (int(a) < 500 and amount >= 450):
        return "KIA", 0.28, "AI-Detectie: Materieel bedrijfsmiddel"
    
    return None, 0, "Geen fiscale match"

# --- 2. DATA PARSER ---
def parse_xaf_ai(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        data = []
        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            tp = re.search(r'<amntTp>(.*?)</amntTp>', line)
            if acc and amnt and tp and tp.group(1) == 'D':
                try:
                    val = float(amnt.group(1).replace(',', '.'))
                    data.append({'acc': acc.group(1), 'desc': desc.group(1) if desc else "", 'val': val})
                except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.set_page_config(page_title="Compliance Sencil AI", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stMetricValue"] { color: #3fb950 !important; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | AI Hub")
st.subheader("Accountancy Intelligence voor Ave Export B.V.")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df_raw = parse_xaf_ai(file.getvalue())
    if not df_raw.empty:
        df_raw = df_raw.drop_duplicates(subset=['desc', 'val'])
        
        final_results = []
        for _, row in df_raw.iterrows():
            label, perc, reason = ai_analyze_transaction(row['desc'], row['val'], row['acc'])
            if label:
                final_results.append({
                    "Subsidie": label,
                    "Omschrijving": row['desc'],
                    "Bedrag (Ex. BTW)": row['val'],
                    "Netto Voordeel": row['val'] * perc,
                    "AI Oordeel": reason
                })
        
        if final_results:
            st.success("AI Analyse voltooid. Kansen gevonden!")
            res_df = pd.DataFrame(final_results)
            
            c1, c2 = st.columns(2)
            totaal_voordeel = res_df['Netto Voordeel'].sum()
            c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {totaal_voordeel:,.2f}")
            c2.metric("AANTAL KANSEN", len(final_results))
            
            st.write("### Gedetailleerd Rapport")
            st.table(res_df.style.format({'Bedrag (Ex. BTW)': '€ {:,.2f}', 'Netto Voordeel': '€ {:,.2f}'}))
        else:
            st.info("Geen subsidiabele activa gevonden na AI-filtering van kosten.")
    else:
        st.error("Kon de data niet inlezen. Controleer het bestand.")
