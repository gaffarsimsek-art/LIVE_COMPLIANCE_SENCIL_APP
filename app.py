import streamlit as st
import pandas as pd
import re

def parse_xaf_final(file_content):
    try:
        text = file_content.decode('latin-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        
        extracted_data = []
        for line in lines:
            acc_match = re.search(r'<accID>(.*?)</accID>', line)
            desc_match = re.search(r'<desc>(.*?)</desc>', line)
            amnt_match = re.search(r'<amnt>(.*?)</amnt>', line)
            
            if acc_match and amnt_match:
                acc = acc_match.group(1)
                desc = desc_match.group(1) if desc_match else ""
                
                # --- FILTER LOGICA ---
                # 1. Alleen Activa rekeningen (Balans < 3000)
                if not (acc.isdigit() and int(acc) < 3000):
                    continue
                
                # 2. Negeer Beginbalans en Afschrijvingen
                negeer_woorden = ['beginbalans', 'openingsbalans', 'afschrijving', 'afschr', 'depreciation']
                if any(w in desc.lower() for w in negeer_woorden):
                    continue

                try:
                    num_val = abs(float(amnt_match.group(1).replace(',', '.')))
                    if num_val > 0:
                        extracted_data.append({
                            'rekening': acc,
                            'omschrijving': desc,
                            'bedrag': num_val
                        })
                except:
                    continue
        return pd.DataFrame(extracted_data)
    except Exception as e:
        st.error(f"Fout: {e}")
        return pd.DataFrame()

def analyseer_subsidies(df):
    results = []
    if df.empty: return results
    
    # Voorkom dubbele boekingen
    df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
    
    for _, row in df.iterrows():
        d = str(row['omschrijving']).lower()
        b = row['bedrag']
        
        # Investerings-check (Enkel op Activa zijde, boven de drempel)
        if b >= 450:
            type_v = "KIA"
            perc = 0.28
            
            # MIA/EIA als het specifiek groen is
            if any(x in d for x in ['elek', 'zon', 'laad', 'warmte']):
                type_v = "MIA/EIA"
                perc = 0.135
            
            results.append({
                "Type": f"{type_v} Potentieel",
                "Item": row['omschrijving'],
                "Investering": b,
                "Fiscaal Voordeel": b * perc
            })
                
    return results

# UI blijft hetzelfde...
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.markdown("<style>.stApp { background-color: #0b0e14; color: white; }</style>", unsafe_allow_html=True)
st.title("🛡️ Compliance Sencil | Activa Scan")

file = st.file_uploader("Upload Snelstart Auditfile (.xaf)", type=["xaf"])

if file:
    df = parse_xaf_final(file.getvalue())
    if not df.empty:
        hits = analyseer_subsidies(df)
        c1, c2, c3 = st.columns(3)
        totaal = sum([h['Fiscaal Voordeel'] for h in hits])
        c1.metric("FISCAAL VOORDEEL 2024", f"€ {totaal:,.2f}")
        c2.metric("NIEUWE ACTIVA GEVONDEN", len(hits))
        c3.metric("FOCUS", "BALANS (ACTIVA)")
        
        if hits:
            st.table(pd.DataFrame(hits))
        else:
            st.info("Geen nieuwe activa-investeringen gevonden boven de €450.")
