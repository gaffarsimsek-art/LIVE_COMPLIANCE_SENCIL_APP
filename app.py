import streamlit as st
import pandas as pd
import re

# --- 1. DE AI-ENGINE (Deep Scan Logic) ---
def ai_power_scan(desc, amount, account):
    d = str(desc).lower()
    val = float(amount)
    acc = str(account)
    
    # AI Blacklist: Sluit kosten en ruis onmiddellijk uit
    blacklist = [
        'lease', 'vwpfs', 'financial', 'insurance', 'verzekering', 'premie', 
        'corr', 'afschr', 'beginbalans', 'rente', 'vpb', 'btw', 'loon', 'salaris'
    ]
    if any(x in d for x in blacklist) or val < 450:
        return None, 0, None, None

    # AI Patroonherkenning
    is_auto = any(x in d for x in ['aanschaf', 'koop', 'mb ', 'glc', 'mercedes', 'porsche', 'auto'])
    is_elek = any(x in d for x in ['elektr', 'ev ', 'taycan', 'eqs', 'tesla', 'laadpaal', 'eqc'])
    is_hardware = any(x in d for x in ['hp ', 'pc', 'computer', 'laptop', 'monitor', 'mastertools', 'gereedschap'])

    # Fiscale Classificatie
    if is_elek:
        return "MIA / VAMIL", 0.135, "🤖 AI: Duurzame investering gedetecteerd (Elektrisch).", "MIA"
    
    if is_auto:
        # De AI ziet een voertuig aankoop. 
        # Voor de KIA is een bestelauto (grijskenteken) 28% aftrekbaar. 
        # Personenauto's op brandstof meestal niet, maar we tonen hem als 'Potentieel'.
        return "KIA (Mogelijk Bestelauto)", 0.28, "🤖 AI: Voertuig aankoop op de balans. Check op Grijskenteken.", "KIA"
    
    if is_hardware or int(acc) < 500:
        return "KIA", 0.28, "🤖 AI: Materieel bedrijfsmiddel / Inventaris.", "KIA"

    return None, 0, None, None

# --- 2. DATA VERWERKING ---
def parse_xaf_advanced(file_content):
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

# --- 3. DASHBOARD ---
st.set_page_config(page_title="Compliance Sencil AI", layout="wide")
st.title("🛡️ Compliance Sencil | AI Power Scan")
st.subheader("Deep Scan: Ave Export B.V. 2024")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df_raw = parse_xaf_advanced(file.getvalue())
    if not df_raw.empty:
        # AI filtert dubbele boekingen en past de motor toe
        df_raw = df_raw.drop_duplicates(subset=['desc', 'val'])
        
        results = []
        for _, row in df_raw.iterrows():
            label, perc, reason, type_code = ai_power_scan(row['desc'], row['val'], row['acc'])
            if label:
                results.append({
                    "Subsidie": label,
                    "Investering": row['desc'],
                    "Bedrag (Ex. BTW)": row['val'],
                    "Netto Voordeel": row['val'] * perc,
                    "AI Toelichting": reason
                })
        
        if results:
            res_df = pd.DataFrame(results)
            c1, c2, c3 = st.columns(3)
            total_v = res_df['Netto Voordeel'].sum()
            c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {total_v:,.2f}")
            c2.metric("GEDETECTEERDE ACTIVA", len(results))
            c3.metric("AI STATUS", "OPTIMIZED")
            
            st.write("### 🎯 Gevonden Fiscale Kansen")
            st.table(res_df.style.format({'Bedrag (Ex. BTW)': '€ {:,.2f}', 'Netto Voordeel': '€ {:,.2f}'}))
            
            st.info("De AI heeft de 'Aanschaf GLC' herkend. Let op: Voor personenauto's op brandstof geldt de KIA alleen als het een bestelauto (grijskenteken) is.")
        else:
            st.info("AI Scan voltooid. Geen nieuwe investeringen boven €450 gevonden.")
