import streamlit as st
import pandas as pd
import re

# 1. HULPFUNCTIES
def extract_kenteken(text):
    patroon = r'\b([A-Z0-9]{2}-?[A-Z0-9]{2}-?[A-Z0-9]{2}|[A-Z]{1}-?\d{3}-?[A-Z]{2})\b'
    match = re.search(patroon, str(text).upper())
    return match.group(0) if match else None

def parse_xaf_final_expert(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        data = []
        
        # STRENGE BLACKLIST (Geen kosten, geen lease, geen verzekering)
        blacklist = [
            'vwpfs', 'mercedes-benz fin', 'financial', 'lease', 'insurance', 
            'verzekering', 'wa casco', 'premie', 'corr', 'afschr', 'termijn', 
            'rente', 'beginbalans', 'opening', 'onderhoud', 'service', 'vpb', 'btw'
        ]

        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            tp = re.search(r'<amntTp>(.*?)</amntTp>', line)
            
            if acc and amnt and tp:
                acc_id = acc.group(1)
                description = desc.group(1) if desc else "Geen omschrijving"
                clean_desc = description.lower()
                
                # 1. Alleen Activa-rekeningen (Materiële Vaste Activa < 500)
                if acc_id.isdigit() and int(acc_id) < 500:
                    
                    # 2. Filter op blacklist
                    if any(x in clean_desc for x in blacklist):
                        continue

                    # 3. Alleen toenames (Debet)
                    if tp.group(1) == 'D':
                        try:
                            val = float(amnt.group(1).replace(',', '.'))
                            if val >= 450: # Fiscale ondergrens
                                data.append({
                                    'rekening': acc_id,
                                    'omschrijving': description,
                                    'bedrag': val
                                })
                        except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# 2. UI DESIGN
st.set_page_config(page_title="Compliance Sencil | Fiscal Expert", layout="wide")
st.title("🛡️ Compliance Sencil | Enterprise Hub")
st.subheader("Geavanceerde Subsidie- en Activascan")

uploaded_file = st.file_uploader("Upload .xaf bestand van Ave Export", type=["xaf"])

if uploaded_file:
    df = parse_xaf_final_expert(uploaded_file.getvalue())
    
    if not df.empty:
        df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
        
        st.write("### 🔍 Gedetecteerde Materiële Activa")
        st.info("Onderstaande posten zijn herkend als nieuwe investeringen op de balans.")
        
        items = []
        for _, row in df.iterrows():
            ken = extract_kenteken(row['omschrijving'])
            items.append({
                "Investering": row['omschrijving'],
                "Bedrag (Ex. BTW)": row['bedrag'],
                "Kenteken": ken if ken else "Inventaris/Machine"
            })
        
        st.table(pd.DataFrame(items).style.format({'Bedrag (Ex. BTW)': '€ {:,.2f}'}))

        # DE EXPERT BUTTON
        st.write("---")
        if st.button("🚀 CLASSIFICEER SUBSIDIE-TYPES (KIA / MIA / EIA / VAMIL)"):
            st.subheader("🎯 Fiscaal Advies Rapportage")
            
            final_hits = []
            for item in items:
                d = item['Investering'].lower()
                b = item['Bedrag (Ex. BTW)']
                ken = item['Kenteken']
                
                # CLASSIFICATIE LOGICA
                label = ""
                perc = 0.0
                toelichting = ""

                # 1. MIA / VAMIL (Milieu-investeringen)
                if any(x in d for x in ['elektr', 'taycan', 'ev ', 'eqs', 'tesla', 'e-tron', 'laadpaal', 'laadstation']):
                    label = "MIA / VAMIL"
                    perc = 0.135 # Netto gemiddeld voordeel
                    toelichting = "Milieu-investeringsaftrek voor emissieloos vervoer."
                
                # 2. EIA (Energie-investeringen)
                elif any(x in d for x in ['zonne', 'led', 'warmtepomp', 'isolatie', 'energiezuinig']):
                    label = "EIA"
                    perc = 0.11 # Netto gemiddeld voordeel
                    toelichting = "Energie-investeringsaftrek voor energiebesparende middelen."
                
                # 3. KIA (Kleinschaligheid - Algemene bedrijfsmiddelen)
                elif ken == "Inventaris/Machine" or any(x in d for x in ['hp', 'computer', 'laptop', 'macbook', 'pc', 'meubilair']):
                    label = "KIA"
                    perc = 0.28 # Fiscale aftrekpost
                    toelichting = "Kleinschaligheidsinvesteringsaftrek voor algemene activa."
                
                # 4. BRANDSTOF VOERTUIGEN (Uitsluiten)
                elif ken != "Inventaris/Machine":
                    st.warning(f"❌ **{ken}** ({item['Investering']}): Geen KIA/MIA mogelijk voor brandstof-personenauto's.")
                    continue
                
                if label:
                    final_hits.append({
                        "Type": label,
                        "Omschrijving": item['Investering'],
                        "Bedrag": b,
                        "Netto Voordeel": b * perc,
                        "Toelichting": toelichting
                    })
            
            if final_hits:
                st.success("Analyse voltooid!")
                final_df = pd.DataFrame(final_hits)
                st.table(final_df.style.format({'Bedrag': '€ {:,.2f}', 'Netto Voordeel': '€ {:,.2f}'}))
                
                totaal_v = sum([h['Netto Voordeel'] for h in final_hits])
                st.metric("TOTAAL GESCHAT FISCAAL VOORDEEL", f"€ {totaal_v:,.2f}")
                st.caption("Let op: Dit is een indicatie. Voor definitieve KIA-berekening moet het jaarlijkse investeringstotaal tussen € 2.801 en € 387.580 liggen.")
    else:
        st.warning("Geen materiële activa gevonden boven de €450 op rekeningen 0-499.")
