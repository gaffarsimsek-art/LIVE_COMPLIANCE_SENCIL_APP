import streamlit as st
import pandas as pd
import re

# --- AI FISCALE LOGICA ---
def ai_fiscal_guard(desc, amount, account):
    d = str(desc).lower()
    val = float(amount)
    acc = str(account)
    
    # 1. HARDE BLOKKADES (De 'Nee, tenzij' fase)
    if val < 450:
        return None, 0, "Bedrag onder fiscale grens van €450."
    
    blacklist = [
        'loon', 'salaris', 'sociale lasten', 'vpb', 'btw', 'pension', 
        'lease', 'vwpfs', 'mercedes-benz fin', 'insurance', 'verzekering', 
        'wa casco', 'premie', 'corr', 'afschr', 'rente', 'beginbalans'
    ]
    if any(x in d for x in blacklist):
        return None, 0, "Gemarkeerd als loonkosten, belasting of exploitatie (geen investering)."

    # 2. CLASSIFICATIE (De 'Welke subsidie' fase)
    # MIA/Vamil (Duurzaam vervoer)
    if any(x in d for x in ['elektr', 'taycan', 'ev ', 'eqs', 'tesla', 'laadpaal', 'laadstation']):
        return "MIA / Vamil", 0.135, "AI-Check: Duurzame mobiliteit gedetecteerd."
    
    # EIA (Energiebesparing)
    if any(x in d for x in ['zonne', 'led', 'warmtepomp', 'isolatie', 'eia']):
        return "EIA", 0.11, "AI-Check: Energiebesparende investering."
    
    # KIA (Algemene inventaris/computer)
    # We kijken naar rekeningnummers onder 500 (Balans) en trefwoorden
    if int(acc) < 500 or any(x in d for x in ['hp ', 'computer', 'laptop', 'macbook', 'pc', 'monitor', 'inventaris', 'machine']):
        return "KIA", 0.28, "AI-Check: Materieel bedrijfsmiddel (Hardware/Inventaris)."

    return None, 0, "Geen duidelijke match voor investeringssubsidie."

# --- DATA PARSER ---
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
st.title("🛡️ Compliance Sencil | AI Enterprise Hub")
st.subheader("Gezuiverde Fiscale Analyse voor Ave Export B.V.")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df_raw = parse_xaf_final(file.getvalue())
    if not df_raw.empty:
        df_raw = df_raw.drop_duplicates(subset=['desc', 'val'])
        
        final_hits = []
        for _, row in df_raw.iterrows():
            label, perc, reason = ai_fiscal_guard(row['desc'], row['val'], row['acc'])
            if label:
                final_hits.append({
                    "Subsidie": label,
                    "Omschrijving": row['desc'],
                    "Bedrag (Ex. BTW)": row['val'],
                    "Netto Voordeel": row['val'] * perc,
                    "AI Toelichting": reason
                })
        
        if final_hits:
            res_df = pd.DataFrame(final_hits)
            c1, c2 = st.columns(2)
            c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {res_df['Netto Voordeel'].sum():,.2f}")
            c2.metric("AANTAL INVESTERINGEN", len(final_hits))
            
            st.write("### 🎯 Gevalideerde Investeringen")
            st.table(res_df.style.format({'Bedrag (Ex. BTW)': '€ {:,.2f}', 'Netto Voordeel': '€ {:,.2f}'}))
        else:
            st.info("De AI heeft de balans gescand. Geen nieuwe investeringen boven €450 gevonden (kosten en loon succesvol gefilterd).")
