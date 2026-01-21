import streamlit as st
import pandas as pd
import re

# --- 1. HULPFUNCTIES (KENTEKENS) ---
def extract_kenteken(text):
    patroon = r'\b([A-Z0-9]{2}-?[A-Z0-9]{2}-?[A-Z0-9]{2}|[A-Z]{1}-?\d{3}-?[A-Z]{2})\b'
    match = re.search(patroon, str(text).upper())
    return match.group(0) if match else None

# --- 2. DE AI ACCOUNTANT MOTOR ---
def ai_accountant_decision(desc, amount, account):
    d = str(desc).lower()
    val = float(amount)
    acc = str(account)
    
    # HARDE UITSLUITING (De AI herkent kosten die geen activa zijn)
    # Zelfs als deze boven de 450 euro zijn, worden ze hier geblokkeerd.
    garbage_terms = [
        'vwpfs', 'mercedes-benz fin', 'financial', 'insurance', 'verzekering', 
        'wa casco', 'premie', 'flower', 'bloemen', 'payment', 'vpb', 'btw', 
        'loon', 'salaris', 'pension', 'afschrijving', 'rente', 'service', 
        'onderhoud', 'corr', 'beginbalans', 'opening'
    ]
    
    if any(x in d for x in garbage_terms):
        return None, 0, "AI: Gedetecteerd als exploitatiekosten/correctie."

    # FISCALE GRENS
    if val < 450:
        return None, 0, "AI: Bedrag onder fiscale activatiegrens (€450)."

    # CLASSIFICATIE VAN ECHTE ACTIVA
    # A. Vervoermiddelen (MIA/KIA check)
    if any(x in d for x in ['aanschaf', 'koop', 'mercedes', 'glc', 'mb ', 'porsche', 'taycan', 'auto']):
        is_elek = any(x in d for x in ['elektr', 'ev ', 'eqs', 'eqc', 'tesla', 'taycan', 'e-tron'])
        if is_elek:
            return "MIA / VAMIL", 0.135, "AI: Elektrisch vervoermiddel (MIA-gerechtigd)."
        else:
            # Voor brandstofauto's: Alleen KIA als het een bestelauto (grijskenteken) is
            return "KIA (Check: Grijskenteken?)", 0.28, "AI: Voertuig aanschaf op balans. Controleer op bestelauto-status."

    # B. Inventaris & Hardware (KIA)
    if any(x in d for x in ['hp ', 'pc', 'computer', 'laptop', 'monitor', 'mastertools', 'gereedschap', 'inventaris', 'meubilair']):
        return "KIA", 0.28, "AI: Materiële investering (Hardware/Gereedschap)."

    # C. Balans-activatie Fallback
    if int(acc) < 500:
        return "KIA (Balans)", 0.28, "AI: Activering op balansrekening gedetecteerd."

    return None, 0, "AI: Geen duidelijke investeringsmatch."

# --- 3. PARSER ---
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
            # Alleen Debet (inkoop/activatie)
            if acc and amnt and tp and tp.group(1) == 'D':
                try:
                    num = float(amnt.group(1).replace(',', '.'))
                    data.append({'acc': acc.group(1), 'desc': desc.group(1) if desc else "", 'val': num})
                except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# --- 4. DASHBOARD ---
st.set_page_config(page_title="Compliance Sencil AI", layout="wide")
st.title("🛡️ Compliance Sencil | Accountant AI")
st.subheader("Fiscale Audit: Ave Export B.V.")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df_raw = parse_xaf_advanced(file.getvalue())
    if not df_raw.empty:
        df_raw = df_raw.drop_duplicates(subset=['desc', 'val'])
        
        final_hits = []
        for _, row in df_raw.iterrows():
            label, perc, reason = ai_accountant_decision(row['desc'], row['val'], row['acc'])
            if label:
                final_hits.append({
                    "Subsidie Type": label,
                    "Investering": row['desc'],
                    "Bedrag (Ex. BTW)": row['val'],
                    "Netto Voordeel": row['val'] * perc,
                    "AI Toelichting": reason
                })
        
        if final_hits:
            res_df = pd.DataFrame(final_hits)
            c1, c2 = st.columns(2)
            totaal_v = res_df['Netto Voordeel'].sum()
            c1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {totaal_v:,.2f}")
            c2.metric("GEDETECTEERDE ACTIVA", len(final_hits))
            
            st.write("### 🎯 Gevalideerde Investeringen")
            st.table(res_df.style.format({'Bedrag (Ex. BTW)': '€ {:,.2f}', 'Netto Voordeel': '€ {:,.2f}'}))
        else:
            st.info("AI Scan voltooid. Geen nieuwe investeringen boven €450 gevonden (Alle kosten succesvol gefilterd).")
