import streamlit as st
import pandas as pd
import re

# 1. FUNCTIES
def extract_kenteken(text):
    patroon = r'\b([A-Z0-9]{2}-?[A-Z0-9]{2}-?[A-Z0-9]{2}|[A-Z]{1}-?\d{3}-?[A-Z]{2})\b'
    match = re.search(patroon, str(text).upper())
    return match.group(0) if match else None

def parse_xaf_ultra_safe(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        data = []
        
        # Harde uitsluitlijst voor lease en kosten
        blacklist = ['vwpfs', 'mercedes-benz fin', 'financial', 'lease', 'insurance', 'verzekering', 'wa casco', 'premie', 'corr', 'afschr', 'termijn']

        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            tp = re.search(r'<amntTp>(.*?)</amntTp>', line)
            
            if acc and amnt and tp:
                description = desc.group(1) if desc else ""
                clean_desc = description.lower()
                
                # Check blacklist
                if any(x in clean_desc for x in blacklist):
                    continue

                # Alleen Balans (Activa < 3000) en Debet (Inkoop)
                if acc.group(1).isdigit() and int(acc.group(1)) < 3000 and tp.group(1) == 'D':
                    try:
                        val = float(amnt.group(1).replace(',', '.'))
                        if val >= 450:
                            data.append({'rekening': acc.group(1), 'omschrijving': description, 'bedrag': val})
                    except: continue
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Fout bij verwerken bestand: {e}")
        return pd.DataFrame()

# 2. UI DESIGN
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.title("🛡️ Compliance Sencil | Precision Hub")

uploaded_file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if uploaded_file:
    df = parse_xaf_ultra_safe(uploaded_file.getvalue())
    
    if not df.empty:
        # Filter dubbelingen
        df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
        
        st.subheader("🔍 Potentiële Activa (Gefilterd op Balans)")
        
        results = []
        for _, row in df.iterrows():
            ken = extract_kenteken(row['omschrijving'])
            results.append({
                "Activa": row['omschrijving'],
                "Bedrag": row['bedrag'],
                "Kenteken": ken if ken else "Geen voertuig"
            })
        
        res_df = pd.DataFrame(results)
        st.table(res_df.style.format({'Bedrag': '€ {:,.2f}'}))

        # DE RDW CHECK KNOP
        st.write("---")
        if st.button("🏁 START RDW & SUBSIDIE CHECK"):
            st.subheader("🎯 Resultaten Fiscale Analyse")
            
            final_list = []
            for item in results:
                d = item['Activa'].lower()
                # RDW Logica: Alleen MIA als het elektrisch is
                is_elek = any(x in d for x in ['elektr', 'taycan', 'ev', 'eqs', 'e-tron', 'tesla'])
                
                # Als het een voertuig is maar niet elektrisch -> overslaan (geen MIA/KIA voor brandstof personenauto)
                if item['Kenteken'] != "Geen voertuig" and not is_elek:
                    st.write(f"❌ {item['Kenteken']} ({item['Activa']}): Overgeslagen (Brandstofvoertuig)")
                    continue
                
                perc = 0.135 if is_elek else 0.28
                cat = "MIA / VAMIL" if is_elek else "KIA"
                
                final_list.append({
                    "Regeling": cat,
                    "Investering": item['Activa'],
                    "Bedrag": item['Bedrag'],
                    "Fiscaal Voordeel": item['Bedrag'] * perc
                })
            
            if final_list:
                final_df = pd.DataFrame(final_list)
                st.success("Analyse voltooid!")
                st.table(final_df.style.format({'Bedrag': '€ {:,.2f}', 'Fiscaal Voordeel': '€ {:,.2f}'}))
                
                totaal_v = sum([h['Fiscaal Voordeel'] for h in final_list])
                st.metric("TOTAAL FISCAAL VOORDEEL", f"€ {totaal_v:,.2f}")
            else:
                st.info("Geen subsidiabele posten gevonden na RDW check.")
    else:
        st.warning("Geen activa gevonden. Controleer of dit een export van de balans is.")
