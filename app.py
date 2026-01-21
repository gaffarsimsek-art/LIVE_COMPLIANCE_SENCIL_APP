import streamlit as st
import pandas as pd
import re

# --- 1. CONFIGURATIE ---
# Alleen deze rekeningen uit de administratie van Ave Export zijn relevante activa
VALID_ASSET_ACCOUNTS = ['100', '200'] # 100 = Inventaris, 200 = Vervoermiddelen

def extract_kenteken(text):
    patroon = r'\b([A-Z0-9]{2}-?[A-Z0-9]{2}-?[A-Z0-9]{2}|[A-Z]{1}-?\d{3}-?[A-Z]{2})\b'
    match = re.search(patroon, str(text).upper())
    return match.group(0) if match else None

# --- 2. DE STRENGSTE PARSER ---
def parse_xaf_strict_ledger(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        data = []
        
        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            tp = re.search(r'<amntTp>(.*?)</amntTp>', line)
            
            if acc and amnt and tp:
                acc_id = acc.group(1).strip()
                
                # STRENG FILTER: Alleen rekening 100 of 200
                if acc_id in VALID_ASSET_ACCOUNTS:
                    # Alleen Debet (D) = Bijschrijving op de activa
                    if tp.group(1) == 'D':
                        val = float(amnt.group(1).replace(',', '.'))
                        # Fiscale grens
                        if val >= 450:
                            data.append({
                                'Account': acc_id,
                                'Omschrijving': desc.group(1) if desc else "Geen omschrijving",
                                'Bedrag': val
                            })
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Fout bij inlezen: {e}")
        return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.set_page_config(page_title="Compliance Sencil | Accountant Mode", layout="wide")
st.title("🛡️ Compliance Sencil | Accountant Mode")
st.subheader("Grootboek-audit: Ave Export B.V.")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df = parse_xaf_strict_ledger(file.getvalue())
    
    if not df.empty:
        # Dubbele boekingen verwijderen
        df = df.drop_duplicates(subset=['Omschrijving', 'Bedrag'])
        
        st.write("### ✅ Gevalideerde Activa (Rekening 100 & 200)")
        st.info("Alle overige rekeningen (kosten, loon, lease) zijn door de accountant-filter geblokkeerd.")
        
        results = []
        for _, row in df.iterrows():
            d = row['Omschrijving'].lower()
            b = row['Bedrag']
            acc = row['Account']
            
            # AI Classificatie op basis van de geselecteerde activa
            label = "KIA"
            perc = 0.28
            toelichting = "Materiële activa (Inventaris)"
            
            if acc == '200':
                # Check of het een elektrische auto is (MIA)
                if any(x in d for x in ['elektr', 'ev ', 'eqs', 'taycan', 'tesla', 'laad']):
                    label = "MIA / Vamil"
                    perc = 0.135
                    toelichting = "Milieu-investering (Elektrisch)"
                else:
                    label = "KIA (Check)"
                    toelichting = "Vervoermiddel op balans. Alleen KIA bij grijs kenteken."
            
            results.append({
                "Regeling": label,
                "Grootboek": acc,
                "Investering": row['Omschrijving'],
                "Bedrag (Ex. BTW)": b,
                "Netto Voordeel": b * perc,
                "Toelichting": toelichting
            })
            
        res_df = pd.DataFrame(results)
        st.table(res_df.style.format({'Bedrag (Ex. BTW)': '€ {:,.2f}', 'Netto Voordeel': '€ {:,.2f}'}))
        
        totaal = res_df['Netto Voordeel'].sum()
        st.metric("TOTAAL FISCAAL VOORDEEL", f"€ {totaal:,.2f}")
    else:
        st.warning("Geen nieuwe investeringen gevonden op de activa-rekeningen (100 & 200).")
