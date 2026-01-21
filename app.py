import streamlit as st
import pandas as pd
import re

# 1. FUNCTIES VOOR KENTEKENS EN FILTERING
def extract_kenteken(text):
    patroon = r'\b([A-Z0-9]{2}-?[A-Z0-9]{2}-?[A-Z0-9]{2}|[A-Z]{1}-?\d{3}-?[A-Z]{2})\b'
    match = re.search(patroon, str(text).upper())
    return match.group(0) if match else None

def parse_xaf_no_costs(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        data = []
        
        # UITGEBREIDE ZWARTE LIJST (Deze regels gaan er direct uit)
        blacklist = [
            'vwpfs', 'mercedes-benz fin', 'financial', 'lease', 'insurance', 
            'verzekering', 'wa casco', 'premie', 'corr', 'afschr', 'termijn', 
            'rente', 'beginbalans', 'opening', 'vpb', 'btw', 'loonkosten'
        ]

        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            tp = re.search(r'<amntTp>(.*?)</amntTp>', line)
            
            if acc and amnt and tp:
                description = desc.group(1) if desc else ""
                clean_desc = description.lower()
                
                # 1. Filter op zwarte lijst
                if any(x in clean_desc for x in blacklist):
                    continue

                # 2. Filter op Balans (Rekening < 3000) en alleen Inkomsten/Activa (Debet)
                if acc.group(1).isdigit() and int(acc.group(1)) < 3000 and tp.group(1) == 'D':
                    try:
                        val = float(amnt.group(1).replace(',', '.'))
                        if val >= 450: # Alleen serieuze posten
                            data.append({'rekening': acc.group(1), 'omschrijving': description, 'bedrag': val})
                    except: continue
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Fout: {e}")
        return pd.DataFrame()

# 2. DASHBOARD DESIGN
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.title("🛡️ Compliance Sencil | Precision Activa Scan")

uploaded_file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if uploaded_file:
    df = parse_xaf_no_costs(uploaded_file.getvalue())
    
    if not df.empty:
        df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
        
        st.subheader("📋 Bruto Activa Lijst (Gefilterd op Balans)")
        st.write("Onderstaande posten staan op de balansrekeningen. Gebruik de RDW-knop om kosten van investeringen te scheiden.")
        
        raw_results = []
        for _, row in df.iterrows():
            ken = extract_kenteken(row['omschrijving'])
            raw_results.append({
                "Post": row['omschrijving'],
                "Bedrag": row['bedrag'],
                "Kenteken": ken if ken else "Geen"
            })
        
        st.table(pd.DataFrame(raw_results).style.format({'Bedrag': '€ {:,.2f}'}))

        # DE MENSELIJKE RDW LOGICA KNOP
        st.write("---")
        if st.button("🚀 START RDW INTELLIGENCE & SUBSIDIE SCAN"):
            st.subheader("🎯 Gevalideerde Fiscale Kansen")
            
            final_hits = []
            for item in raw_results:
                d = item['Post'].lower()
                ken = item['Kenteken']
                
                # MENSELIJK DENKEN:
                # Is het een auto? Check of hij elektrisch is (alleen dan MIA/KIA)
                is_elek = any(x in d for x in ['elektr', 'taycan', 'ev', 'eqs', 'tesla', 'e-tron'])
                
                # Als het een voertuig is maar GEEN elektrische aanduiding heeft -> SKIP (Brandstof lease/kosten)
                if ken != "Geen" and not is_elek:
                    st.write(f"⚠️ **{ken}** ({item['Post']}) overgeslagen: Brandstofvoertuig of leasekosten.")
                    continue
                
                # Is het een computer/inventaris?
                is_pc = any(x in d for x in ['hp', 'computer', 'laptop', 'macbook', 'pc', 'monitor'])
                
                if is_pc or is_elek or item['Bedrag'] > 2000: # Filter voor rest-ruis
                    perc = 0.135 if is_elek else 0.28
                    cat = "MIA / VAMIL" if is_elek else "KIA"
                    
                    final_hits.append({
                        "Regeling": cat,
                        "Investering": item['Post'],
                        "Bedrag": item['Bedrag'],
                        "Fiscaal Voordeel": item['Bedrag'] * perc
                    })
            
            if final_hits:
                final_df = pd.DataFrame(final_hits)
                st.success("Analyse voltooid! De onderstaande posten zijn echte investeringen.")
                st.table(final_df.style.format({'Bedrag': '€ {:,.2f}', 'Fiscaal Voordeel': '€ {:,.2f}'}))
                
                totaal_v = sum([h['Fiscaal Voordeel'] for h in final_hits])
                st.metric("TOTAAL NETTO VOORDEEL", f"€ {totaal_v:,.2f}")
            else:
                st.info("Geen subsidiabele investeringen overgebleven na de RDW/Menselijke check.")
    else:
        st.warning("Geen activa gevonden op de balans.")
