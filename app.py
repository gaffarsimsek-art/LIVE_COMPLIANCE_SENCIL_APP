import streamlit as st
import pandas as pd
import re

# --- AI ANALYSE LOGICA ---
def ai_fiscal_classifier(description, amount, account):
    d = str(description).lower()
    
    # 1. AI "Noise" Detectie (Is het een kost of een investering?)
    # De AI herkent patronen die duiden op exploitatiekosten (geen MIA/KIA)
    noise_patterns = ['lease', 'financial', 'insurance', 'verzekering', 'wa casco', 'premie', 'corr', 'afschr', 'onderhoud', 'vwpfs', 'rente', 'service']
    if any(x in d for x in noise_patterns):
        return None, "Kosten/Lease (Geen investering)"

    # 2. AI "Asset" Detectie (Wat voor soort investering is het?)
    # KIA Check: Fysieke objecten
    if any(x in d for x in ['hp ', 'computer', 'laptop', 'macbook', 'pc', 'monitor', 'meubilair', 'inventaris']):
        return "KIA", "AI-Detectie: Materieel bedrijfsmiddel (Hardware/Inventaris)"
    
    # MIA/Vamil Check: Elektrisch vervoer
    if any(x in d for x in ['elektr', 'taycan', 'ev ', 'eqs', 'tesla', 'e-tron', 'laadpaal']):
        return "MIA / Vamil", "AI-Detectie: Emissieloos vervoermiddel (Duurzaam)"
    
    # EIA Check: Energiebesparing
    if any(x in d for x in ['zonne', 'led', 'warmtepomp', 'eia']):
        return "EIA", "AI-Detectie: Energie-investeringsaftrek"

    # 3. Fallback: Als het op een activa rekening staat en > 450 euro is
    if int(account) < 500 and amount >= 450:
        return "KIA", "AI-Classificatie: Onbekend materieel actief op balans"

    return None, "Geen fiscale match gevonden"

# --- DATA VERWERKING ---
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

# --- INTERFACE ---
st.set_page_config(page_title="Compliance Sencil AI", layout="wide")
st.title("🛡️ Compliance Sencil | AI Enterprise Hub")
st.subheader("Slimme Subsidie Detectie via Natural Language Processing")

file = st.file_uploader("Upload .xaf bestand van Ave Export", type=["xaf"])

if file:
    df = parse_xaf_ai(file.getvalue())
    if not df.empty:
        df = df.drop_duplicates(subset=['desc', 'val'])
        
        st.write("### AI Analyse Resultaten")
        
        final_results = []
        for _, row in df.iterrows():
            label, reason = ai_fiscal_classifier(row['desc'], row['val'], row['acc'])
            
            if label:
                # Bereken het netto voordeel op basis van AI label
                perc = 0.135 if "MIA" in label or "EIA" in label else 0.28
                final_results.append({
                    "Regeling": label,
                    "Investering": row['desc'],
                    "Bedrag": row['val'],
                    "Fiscaal Voordeel": row['val'] * perc,
                    "AI Toelichting": reason
                })
        
        if final_results:
            res_df = pd.DataFrame(final_hits) # Gebruik resultaten van AI
            st.table(pd.DataFrame(final_results).style.format({'Bedrag': '€ {:,.2f}', 'Fiscaal Voordeel': '€ {:,.2f}'}))
            
            totaal = sum([h['Fiscaal Voordeel'] for h in final_results])
            st.metric("TOTAAL AI-GEDETECTEERD VOORDEEL", f"€ {totaal:,.2f}")
        else:
            st.info("De AI heeft de balans gescand maar geen nieuwe investeringen gevonden.")
