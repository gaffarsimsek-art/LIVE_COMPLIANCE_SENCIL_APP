import streamlit as st
import pandas as pd
import re

# --- AI LOGICA MODULE ---
def ai_classify_investment(description, amount, account):
    desc = str(description).lower()
    
    # AI Scoreboard
    is_physical = 0
    is_green = 0
    is_energy = 0
    is_cost = 0

    # 1. Herkenning van kostenpatronen (Negative AI)
    cost_triggers = ['lease', 'financial', 'vwpfs', 'insurance', 'verzekering', 'premie', 'corr', 'rente', 'afschr', 'onderhoud']
    if any(x in desc for x in cost_triggers):
        is_cost += 10

    # 2. Herkenning van fysieke activa (Positive AI)
    asset_triggers = ['hp ', 'computer', 'laptop', 'macbook', 'pc', 'monitor', 'machine', 'inventaris', 'meubilair', 'kast', 'bureau']
    if any(x in desc for x in asset_triggers) or (int(account) < 500 and is_cost < 5):
        is_physical += 5

    # 3. Milieu & Energie triggers
    if any(x in desc for x in ['elektr', 'taycan', 'eqs', 'ev ', 'tesla', 'laadpaal', 'laadstation']):
        is_green += 10
    if any(x in desc for x in ['zonne', 'led', 'warmtepomp', 'isolatie', 'eia']):
        is_energy += 10

    # Eindbeslissing AI
    if is_cost >= 10:
        return None, 0, "Gemarkeerd als exploitatiekosten/lease (geen investering)."
    
    if is_green >= 10:
        return "MIA / Vamil", 0.135, "AI-Detectie: Emissieloos vervoermiddel of laadinfrastructuur."
    elif is_energy >= 10:
        return "EIA", 0.11, "AI-Detectie: Energiebesparende bedrijfsmiddel."
    elif is_physical >= 5 and amount >= 450:
        return "KIA", 0.28, "AI-Detectie: Materieel bedrijfsmiddel (Kleinschaligheidsaftrek)."
    
    return None, 0, "Onvoldoende bewijs voor fiscale claim."

# --- PARSER & UI ---
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
                val = float(amnt.group(1).replace(',', '.'))
                data.append({'acc': acc.group(1), 'desc': desc.group(1) if desc else "", 'val': val})
        return pd.DataFrame(data)
    except: return pd.DataFrame()

st.set_page_config(page_title="Compliance Sencil AI", layout="wide")
st.title("🛡️ Compliance Sencil | AI Enterprise Hub")
st.subheader("Slimme Subsidie Detectie via NLP-Logica")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    raw_df = parse_xaf_ai(file.getvalue())
    if not raw_df.empty:
        raw_df = raw_df.drop_duplicates(subset=['desc', 'val'])
        
        ai_results = []
        for _, row in raw_df.iterrows():
            label, perc, reason = ai_classify_investment(row['desc'], row['val'], row['acc'])
            if label:
                ai_results.append({
                    "Subsidie": label,
                    "Item": row['desc'],
                    "Investering": row['val'],
                    "AI Onderbouwing": reason,
                    "Netto Voordeel": row['val'] * perc
                })
        
        if ai_results:
            st.success(f"AI Analyse voltooid: {len(ai_results)} kansen geïdentificeerd.")
            res_df = pd.DataFrame(ai_results)
            st.table(res_df.style.format({'Investering': '€ {:,.2f}', 'Netto Voordeel': '€ {:,.2f}'}))
            
            totaal = sum([h['Netto Voordeel'] for h in ai_results])
            st.metric("TOTAAL AI-GEDETECTEERD VOORDEEL", f"€ {totaal:,.2f}")
        else:
            st.info("De AI heeft geen subsidiabele investeringen gevonden in dit bestand.")
