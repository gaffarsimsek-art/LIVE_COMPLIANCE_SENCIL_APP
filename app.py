import streamlit as st
import pandas as pd
import re

def parse_xaf_precision(file_content):
    try:
        # ISO-8859-1 is cruciaal voor Snelstart exports
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        
        extracted_data = []
        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            
            if acc and amnt:
                acc_val = acc.group(1)
                desc_val = desc.group(1) if desc else ""
                
                # --- FILTERING ---
                # Alleen Activa (rekeningen onder 3000)
                if not (acc_val.isdigit() and int(acc_val) < 3000):
                    continue
                
                # Negeer Beginbalans & Afschrijvingen
                clean_desc = desc_val.lower()
                if any(x in clean_desc for x in ['beginbalans', 'openingsbalans', 'afschrijving', 'afschr']):
                    continue

                # --- PRECISIE GETALVERWERKING ---
                raw_amnt = amnt.group(1)
                try:
                    # In XAF is de punt (.) altijd de decimaal. 
                    # We verwijderen eventuele andere ruis en maken er een float van.
                    num_val = abs(float(raw_amnt))
                    
                    if num_val > 0:
                        extracted_data.append({
                            'rekening': acc_val,
                            'omschrijving': desc_val,
                            'bedrag': num_val
                        })
                except ValueError:
                    continue
                    
        return pd.DataFrame(extracted_data)
    except Exception as e:
        st.error(f"Systeemfout: {e}")
        return pd.DataFrame()

def scan_subsidies(df):
    results = []
    if df.empty: return results
    
    # Voorkom dubbele regels van dezelfde boeking
    df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
    
    for _, row in df.iterrows():
        b = row['bedrag']
        d = str(row['omschrijving']).lower()
        
        # Fiscale drempel KIA is € 450 per bedrijfsmiddel
        if b >= 450:
            perc = 0.28
            label = "KIA Potentieel"
            
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

# --- UI GEDEELTE ---
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.markdown("<style>.stApp { background-color: #0b0e14; color: white; }</style>", unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Enterprise Hub")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df = parse_xaf_precision(file.getvalue())
    if not df.empty:
        hits = scan_subsidies(df)
        
        c1, c2, c3 = st.columns(3)
        totaal_investering = sum([h['Investering (Ex. BTW)'] for h in hits])
        totaal_voordeel = sum([h['Fiscaal Voordeel'] for h in hits])
        
        c1.metric("TOTALE INVESTERING", f"€ {totaal_investering:,.2f}")
        c2.metric("FISCAAL VOORDEEL", f"€ {totaal_voordeel:,.2f}")
        c3.metric("KANSEN", len(hits))
        
        if hits:
            # Weergave met nette getallen (Punt voor duizendtal, komma voor decimalen)
            res_df = pd.DataFrame(hits)
            st.write("### 🔍 Gedetecteerde Activa")
            st.table(res_df.style.format({
                'Investering (Ex. BTW)': '€ {:,.2f}',
                'Fiscaal Voordeel': '€ {:,.2f}'
            }))
        else:
            st.info("Geen nieuwe investeringen boven € 450 gevonden op de balans.")
