import streamlit as st
import pandas as pd
import re

# --- SLIMME AI CLASSIFICATIE ---
def ai_fiscal_expert(desc, amount, account):
    d = str(desc).lower()
    val = float(amount)
    acc = str(account)
    
    # 1. HARDE FILTERS (Geen loon, geen kleine bedragen, geen verbruik)
    if val < 450:
        return None, 0, "Onder de €450 grens."

    # Uitgebreide lijst met kostenposten (geen activa)
    expense_triggers = [
        'flower', 'bloemen', 'koffie', 'lunch', 'diner', 'representatie',
        'loon', 'salaris', 'sociale lasten', 'vpb', 'btw', 'pension', 
        'lease', 'vwpfs', 'mercedes-benz fin', 'insurance', 'verzekering', 
        'premie', 'corr', 'afschr', 'rente', 'brandstof', 'diesel', 'benzine'
    ]
    
    if any(x in d for x in expense_triggers):
        return None, 0, "AI-Detectie: Verbruiksgoederen of exploitatiekosten (geen activa)."

    # 2. SUBSIDIE CATEGORIEËN
    # MIA/Vamil (Duurzaam)
    if any(x in d for x in ['elektr', 'taycan', 'ev ', 'eqs', 'tesla', 'laadpaal', 'laadstation']):
        return "MIA / Vamil", 0.135, "AI-Check: Duurzame mobiliteit."
    
    # EIA (Energie)
    if any(x in d for x in ['zonne', 'led', 'warmtepomp', 'isolatie', 'eia']):
        return "EIA", 0.11, "AI-Check: Energiebesparende investering."
    
    # KIA (Inventaris / Hardware)
    # We kijken naar rekeningen onder de 500 (Balans) die NIET in de kosten zitten
    if int(acc) < 500 and any(x in d for x in ['hp ', 'computer', 'laptop', 'macbook', 'pc', 'monitor', 'machine', 'inventaris', 'server']):
        return "KIA", 0.28, "AI-Check: Materieel bedrijfsmiddel."

    return None, 0, "Geen duidelijke fiscale investering gevonden."

# --- DATA VERWERKING ---
def parse_xaf_final(file_content):
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
                    num = float(amnt.group(1).replace(',', '.'))
                    data.append({'acc': acc.group(1), 'desc': desc.group(1) if desc else "", 'val': num})
                except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# --- UI ---
st.set_page_config(page_title="Compliance Sencil AI", layout="wide")
st.title("🛡️ Compliance Sencil | AI Precision Hub")
st.subheader("Gezuiverde Fiscale Analyse voor Ave Export B.V.")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df_raw = parse_xaf_final(file.getvalue())
    if not df_raw.empty:
        df_raw = df_raw.drop_duplicates(subset=['desc', 'val'])
        
        final_hits = []
        for _, row in df_raw.iterrows():
            label, perc, reason = ai_fiscal_expert(row['desc'], row['val'], row['acc'])
            if label:
                final_hits.append({
                    "Subsidie": label,
                    "Investering": row['desc'],
                    "Bedrag (Ex. BTW)": row['val'],
                    "Netto Voordeel": row['val'] * perc,
                    "AI Analyse": reason
                })
        
        if final_hits:
            res_df = pd.DataFrame(final_hits)
            c1, c2 = st.columns(2)
            c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {res_df['Netto Voordeel'].sum():,.2f}")
            c2.metric("GECHECKEERDE ACTIVA", len(final_hits))
            
            st.write("### 🎯 Resultaten (Gezuiverd van bloemen, loon & kosten)")
            st.table(res_df.style.format({'Bedrag (Ex. BTW)': '€ {:,.2f}', 'Netto Voordeel': '€ {:,.2f}'}))
        else:
            st.info("De AI heeft de auditfile gescand en alle kosten (zoals bloemen en loon) gefilterd. Geen nieuwe investeringen boven €450 overgebleven.")
