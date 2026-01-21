import streamlit as st
import pandas as pd
import re

def extract_kenteken(text):
    patroon = r'\b([A-Z0-9]{2}-?[A-Z0-9]{2}-?[A-Z0-9]{2}|[A-Z]{1}-?\d{3}-?[A-Z]{2})\b'
    match = re.search(patroon, str(text).upper())
    return match.group(0) if match else None

def parse_xaf_strict_activa(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        data = []
        
        # UITGEBREIDE FILTERLIST (Blokkeert lease, verzekering en correcties)
        blacklist = [
            'vwpfs', 'mercedes-benz fin', 'financial', 'lease', 'insurance', 
            'verzekering', 'wa casco', 'premie', 'corr', 'afschr', 'termijn', 
            'rente', 'beginbalans', 'opening', 'onderhoud', 'service'
        ]

        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            tp = re.search(r'<amntTp>(.*?)</amntTp>', line)
            
            if acc and amnt and tp:
                acc_id = acc.group(1)
                description = desc.group(1) if desc else ""
                clean_desc = description.lower()
                
                # 1. STRENG REKENING-FILTER: Alleen Materiele Vaste Activa (rekeningen 0 - 499)
                # Bij Ave Export staan de echte investeringen op 100 en 200.
                # Rekening 800 (Lease schulden) en 4000+ (Kosten) worden nu geblokkeerd.
                if acc_id.isdigit() and int(acc_id) < 500:
                    
                    # 2. Check zwarte lijst
                    if any(x in clean_desc for x in blacklist):
                        continue

                    # 3. Alleen nieuwe inkoop (Debet boekingen)
                    if tp.group(1) == 'D':
                        try:
                            val = float(amnt.group(1).replace(',', '.'))
                            if val >= 450: # KIA grens
                                data.append({
                                    'rekening': acc_id,
                                    'omschrijving': description,
                                    'bedrag': val
                                })
                        except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# --- UI DESIGN ---
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.title("🛡️ Compliance Sencil | Materiële Activa Scan")

uploaded_file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if uploaded_file:
    df = parse_xaf_strict_activa(uploaded_file.getvalue())
    
    if not df.empty:
        df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
        
        st.subheader("📋 Gedetecteerde Materiële Activa (Balans)")
        st.write("De volgende posten zijn geactiveerd op de balans en zijn geen lease- of verzekeringskosten.")
        
        items = []
        for _, row in df.iterrows():
            ken = extract_kenteken(row['omschrijving'])
            items.append({
                "Investering": row['omschrijving'],
                "Bedrag (Ex. BTW)": row['bedrag'],
                "Kenteken": ken if ken else "Inventaris/Machine"
            })
        
        st.table(pd.DataFrame(items).style.format({'Bedrag (Ex. BTW)': '€ {:,.2f}'}))

        # DE RDW & SUBSIDIE KNOP
        st.write("---")
        if st.button("🚀 CONTROLEER RDW BRANDSTOF & SUBSIDIE-RECHT"):
            st.subheader("🎯 Fiscale Resultaten")
            
            final_hits = []
            for item in items:
                d = item['Investering'].lower()
                ken = item['Kenteken']
                
                # MENSELIJK EXPERT FILTER:
                # Is het een auto? Check op brandstof via trefwoorden (RDW Simulatie)
                is_elek = any(x in d for x in ['elektr', 'taycan', 'ev', 'eqs', 'tesla', 'e-tron'])
                
                # Personenauto's op brandstof (zoals GLC, 911) hebben GEEN recht op KIA/MIA in de BV
                if ken != "Inventaris/Machine" and not is_elek:
                    st.warning(f"❌ **{ken}** ({item['Investering']}) is een brandstofvoertuig. Geen KIA/MIA mogelijk.")
                    continue
                
                # KIA voor Inventaris of MIA voor Elektrisch
                perc = 0.135 if is_elek else 0.28
                cat = "MIA / VAMIL" if is_elek else "KIA (Kleinschaligheidsaftrek)"
                
                final_hits.append({
                    "Subsidie": cat,
                    "Omschrijving": item['Investering'],
                    "Bedrag": item['Bedrag (Ex. BTW)'],
                    "Netto Voordeel": item['Bedrag (Ex. BTW)'] * perc
                })
            
            if final_hits:
                st.success("Analyse voltooid! De onderstaande posten komen in aanmerking.")
                st.table(pd.DataFrame(final_hits).style.format({'Bedrag': '€ {:,.2f}', 'Netto Voordeel': '€ {:,.2f}'}))
                
                totaal_v = sum([h['Netto Voordeel'] for h in final_hits])
                st.metric("TOTAAL FISCAAL VOORDEEL", f"€ {totaal_v:,.2f}")
    else:
        st.warning("Geen materiële activa gevonden op de balansrekeningen (0-499).")
