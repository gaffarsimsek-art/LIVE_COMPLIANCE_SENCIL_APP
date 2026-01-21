import streamlit as st
import pandas as pd
import re

# 1. DE ULTIEME PARSER (Getest op Ave Export bestand)
def parse_xaf_final(file_content):
    try:
        # Stap 1: Forceer leesbaarheid, negeer vreemde tekens
        text = file_content.decode('latin-1', errors='ignore')
        
        # Stap 2: Zoek alle regels (trLine)
        # We gebruiken een zeer brede zoekopdracht om niets te missen
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        
        extracted_data = []
        for line in lines:
            # Snelstart specifieke tags uit jouw bestand
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            
            if acc and amnt:
                val = amnt.group(1).replace(',', '.') # Zorg dat komma's punten worden
                try:
                    num_val = abs(float(val))
                    if num_val > 0:
                        extracted_data.append({
                            'rekening': acc.group(1),
                            'omschrijving': desc.group(1) if desc else "Geen omschrijving",
                            'bedrag': num_val
                        })
                except:
                    continue
        return pd.DataFrame(extracted_data)
    except Exception as e:
        st.error(f"Leesfout: {e}")
        return pd.DataFrame()

def analyseer_subsidies(df):
    results = []
    if df.empty: return results
    
    # Verwijder dubbele boekingen
    df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
    
    for _, row in df.iterrows():
        d = str(row['omschrijving']).lower()
        a = str(row['rekening'])
        b = row['bedrag']
        
        # KIA Check (Inventaris, computers, machines)
        # Rekening 100 is Inventaris bij Ave Export
        if a == '100' or any(x in d for x in ['hp ', 'computer', 'laptop', 'server', 'inventaris']):
            if b >= 450:
                results.append({"Type": "KIA (Investeringsaftrek)", "Item": row['omschrijving'], "Bedrag": b, "Fiscaal Voordeel": b * 0.28})
        
        # MIA/EIA Check (Duurzaam)
        elif any(x in d for x in ['elek', 'zonne', 'laad', 'accu', 'warmte']):
            if b > 2000:
                results.append({"Type": "MIA/EIA (Milieu/Energie)", "Item": row['omschrijving'], "Bedrag": b, "Fiscaal Voordeel": b * 0.135})
                
    return results

# 2. HET DASHBOARD
st.set_page_config(page_title="Compliance Sencil", layout="wide")

# Styling: Forceer contrast
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: white; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Enterprise Hub")

file = st.file_uploader("Upload Snelstart Auditfile (.xaf)", type=["xaf"])

if file:
    df = parse_xaf_final(file.getvalue())
    
    if not df.empty:
        hits = analyseer_subsidies(df)
        
        c1, c2, c3 = st.columns(3)
        totaal = sum([h['Fiscaal Voordeel'] for h in hits])
        
        c1.metric("TOTAAL VOORDEEL", f"€ {totaal:,.2f}")
        c2.metric("GEDETECTEERD", len(hits))
        c3.metric("STATUS", "ANALYSE VOLTOOID")
        
        if hits:
            st.write("### Gevonden Investeringskansen")
            st.table(pd.DataFrame(hits))
        else:
            st.info("Geen investeringen boven de drempelwaarde (€450) gevonden.")
    else:
        st.warning("Kon geen transacties vinden. Is dit het juiste XAF bestand?")
else:
    st.info("Upload een bestand om de scan te starten.")
