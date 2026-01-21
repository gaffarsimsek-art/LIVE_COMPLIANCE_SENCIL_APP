import streamlit as st
import pandas as pd
import re

# --- 1. DE ACCOUNTANT AI (STRENG & PRECIES) ---
def ai_accountant_core(desc, amount, account):
    d = str(desc).lower()
    val = float(amount)
    acc = str(account)
    
    # STAP 1: De "Nee-fase" (Onherroepelijke blokkade voor kosten)
    # De AI herkent hier direct dat 'Payment for flowers' of 'VPB' geen activa zijn.
    if val < 450: return None, 0, None
    
    blacklist = [
        'flower', 'bloemen', 'coffee', 'koffie', 'lunch', 'diner', 'payment', 
        'vpb', 'btw', 'tax', 'belasting', 'loon', 'salaris', 'sociale', 
        'insurance', 'verzekering', 'premie', 'wa casco', 'lease', 'vwpfs', 
        'financial', 'rente', 'afschr', 'onderhoud', 'service', 'corr', 'beginbalans'
    ]
    if any(x in d for x in blacklist):
        return None, 0, None

    # STAP 2: De "Ja-fase" (Alleen wat echt tastbaar is)
    # A. Vervoermiddelen (De grote Mercedes GLC)
    if any(x in d for x in ['aanschaf', 'koop', 'glc', 'mercedes', 'mb ', 'porsche', 'auto']):
        is_elek = any(x in d for x in ['elektr', 'ev ', 'eqs', 'eqc', 'tesla', 'taycan', 'e-tron'])
        if is_elek:
            return "MIA / VAMIL", 0.135, "🤖 AI: Elektrisch voertuig (Duurzaam)"
        else:
            return "KIA (Check: Bestelauto?)", 0.28, "🤖 AI: Voertuig aanschaf (Groot materieel)"

    # B. Hardware & Gereedschap (De HP computer & Mastertools)
    if any(x in d for x in ['hp ', 'pc', 'computer', 'laptop', 'monitor', 'mastertools', 'gereedschap', 'inventaris']):
        return "KIA", 0.28, "🤖 AI: Materieel bedrijfsmiddel"

    # Als de AI het niet zeker weet, maar het staat wel op de balans (100-200), toon het als 'Onbekend Actief'
    if int(acc) < 300:
        return "KIA (Balans)", 0.28, "🤖 AI: Investering op balansrekening"

    return None, 0, None

# --- 2. DE PARSER (ZUIVERE DATA) ---
def parse_xaf_clean(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        data = []
        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            tp = re.search(r'<amntTp>(.*?)</amntTp>', line)
            # Alleen Debet-boekingen (Inkoop)
            if acc and amnt and tp and tp.group(1) == 'D':
                try:
                    num = float(amnt.group(1).replace(',', '.'))
                    data.append({'acc': acc.group(1), 'desc': desc.group(1) if desc else "", 'val': num})
                except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# --- 3. DASHBOARD ---
st.set_page_config(page_title="Compliance Sencil AI", layout="wide")
st.title("🛡️ Compliance Sencil | Accountant AI")
st.subheader("Fiscale Audit Ave Export B.V. (2024)")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df_raw = parse_xaf_clean(file.getvalue())
    if not df_raw.empty:
        # Verwijder dubbelingen (AI-zuivering)
        df_raw = df_raw.drop_duplicates(subset=['desc', 'val'])
        
        final_list = []
        for _, row in df_raw.iterrows():
            label, perc, reason = ai_accountant_core(row['desc'], row['val'], row['acc'])
            if label:
                final_list.append({
                    "Subsidie": label,
                    "Item": row['desc'],
                    "Bedrag (Ex. BTW)": row['val'],
                    "Fiscaal Voordeel": row['val'] * perc,
                    "AI Toelichting": reason
                })
        
        if final_list:
            res_df = pd.DataFrame(final_list)
            
            # Metrics
            c1, c2, c3 = st.columns(3)
            totaal_v = res_df['Fiscaal Voordeel'].sum()
            c1.metric("TOTAAL VOORDEEL", f"€ {totaal_v:,.2f}")
            c2.metric("INVESTERINGEN", len(final_list))
            c3.metric("STATUS", "GEFILTERD")
            
            st.write("### 🎯 Gevalideerde Investeringen")
            st.table(res_df.style.format({'Bedrag (Ex. BTW)': '€ {:,.2f}', 'Fiscaal Voordeel': '€ {:,.2f}'}))
        else:
            st.info("De AI heeft alle 2024 data gescand. Alle kosten (bloemen, lease, belasting) zijn succesvol gefilterd. Geen nieuwe investeringen gevonden.")
