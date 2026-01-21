import streamlit as st
import pandas as pd
import re

def parse_xaf_final_v2(file_content):
    try:
        # ISO-8859-1 is de standaard codering voor Snelstart XAF
        text = file_content.decode('iso-8859-1', errors='ignore')
        
        # We zoeken specifiek naar trLine blokken
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        
        data = []
        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            
            if acc and amnt:
                acc_id = acc.group(1)
                description = desc.group(1) if desc else ""
                
                # --- FILTERING ---
                # Alleen Activa (rekeningen onder 3000)
                if not (acc_id.isdigit() and int(acc_id) < 3000):
                    continue
                
                # Sla beginbalans en afschrijvingen over
                clean_desc = description.lower()
                if any(x in clean_desc for x in ['beginbalans', 'openingsbalans', 'afschrijving', 'afschr']):
                    continue

                # --- PRECIEZE GETALVERWERKING ---
                # Snelstart XML gebruikt de punt (.) voor decimalen: 1652.07
                raw_amnt = amnt.group(1).strip()
                try:
                    # We maken er een float van. In Python is de punt de standaard decimaal.
                    clean_val = float(raw_amnt)
                    if clean_val != 0:
                        data.append({
                            'rekening': acc_id,
                            'omschrijving': description,
                            'bedrag': abs(clean_val)
                        })
                except ValueError:
                    continue
                    
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Fout in parser: {e}")
        return pd.DataFrame()

def scan_boekhouding(df):
    results = []
    if df.empty: return results
    
    # Voorkom dubbele boekingen op dezelfde omschrijving/bedrag
    df_unique = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
    
    for _, row in df_unique.iterrows():
        b = row['bedrag']
        d = str(row['omschrijving']).lower()
        
        # Fiscale KIA drempel
        if b >= 450:
            perc = 0.28
            label = "KIA Potentieel"
            
            # MIA/EIA check
            if any(x in d for x in ['elek', 'zon', 'laad', 'warmte']):
                perc = 0.135
                label = "MIA/EIA Potentieel"
            
            results.append({
                "Type": label,
                "Item": row['omschrijving'],
                "Investering (Ex. BTW)": b,
                "Fiscaal Voordeel": b * perc
            })
    return results

# --- DASHBOARD LAYOUT ---
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.markdown("<style>.stApp { background-color: #0b0e14; color: white; } [data-testid='stMetricValue'] { color: #00ff41 !important; font-family: monospace; }</style>", unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Precision Hub")

file = st.file_uploader("Upload .xaf van Ave Export", type=["xaf"])

if file:
    df = parse_xaf_final_v2(file.getvalue())
    if not df.empty:
        hits = scan_boekhouding(df)
        
        c1, c2, c3 = st.columns(3)
        totaal_inv = sum([h['Investering (Ex. BTW)'] for h in hits])
        totaal_voord = sum([h['Fiscaal Voordeel'] for h in hits])
        
        # Metrics met Europese punt/komma weergave
        c1.metric("TOTALE INVESTERING", f"€ {totaal_inv:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c2.metric("FISCAAL VOORDEEL", f"€ {totaal_voord:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c3.metric("KANSEN", len(hits))
        
        if hits:
            st.write("### 🔍 Gedetecteerde Activa")
            res_df = pd.DataFrame(hits)
            # Nette tabel-weergave
            st.table(res_df.style.format({
                'Investering (Ex. BTW)': '€ {:,.2f}',
                'Fiscaal Voordeel': '€ {:,.2f}'
            }))
        else:
            st.info("Geen nieuwe activa-investeringen gevonden boven de €450.")
