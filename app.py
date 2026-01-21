import streamlit as st
import pandas as pd
import re

# 1. DE UNIVERSELE SCANNER (Rauwe tekst extractie)
def parse_xaf_raw(file_content):
    # We zetten de file om naar tekst om namespaces te omzeilen
    text = file_content.decode('iso-8859-1', errors='ignore')
    
    # We zoeken met 'regex' naar patronen: Rekening, Omschrijving, Bedrag
    # Dit werkt voor ELK XAF bestand, ook als de XML structuur complex is
    lines = re.findall(r'<trLine>.*?</trLine>', text, re.DOTALL)
    
    data = []
    for line in lines:
        try:
            acc = re.search(r'<accID>(.*?)</accID>', line).group(1)
            desc = re.search(r'<desc>(.*?)</desc>', line).group(1)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line).group(1)
            
            data.append({
                'rekening': acc,
                'omschrijving': desc,
                'bedrag': abs(float(amnt))
            })
        except:
            continue
    return pd.DataFrame(data)

def bereken_voordeel(df):
    results = []
    if df.empty: return results
    
    # Voorkom dubbele regels (Debet/Credit)
    df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
    
    for _, row in df.iterrows():
        d = str(row['omschrijving']).lower()
        a = str(row['rekening'])
        b = row['bedrag']
        
        # Investeringscheck (KIA/MIA/EIA)
        # We pakken de HP Computer op rekening 100 van Ave Export
        is_invest = (a.isdigit() and int(a) < 1000) or any(x in d for x in ['hp', 'comp', 'pc', 'laptop', 'mach'])
        
        if is_invest and b >= 450:
            voordeel_type = "MIA/EIA" if any(x in d for x in ['elek', 'zon', 'laad']) else "KIA"
            perc = 0.135 if voordeel_type == "MIA/EIA" else 0.28
            
            results.append({
                "Type": f"{voordeel_type} Potentieel",
                "Omschrijving": row['omschrijving'],
                "Investering": f"€ {b:,.2f}",
                "Fiscaal Voordeel": b * perc
            })
    return results

# 2. HET DASHBOARD (Zichtbaar & Strak)
st.set_page_config(page_title="Compliance Sencil", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: white; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 40px; }
    .stDataFrame { background-color: #161b22; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Enterprise Hub")
st.subheader("Live Subsidie Analyse")

uploaded_file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if uploaded_file:
    df = parse_xaf_raw(uploaded_file.getvalue())
    if not df.empty:
        hits = bereken_voordeel(df)
        
        c1, c2, c3 = st.columns(3)
        totaal = sum([h['Fiscaal Voordeel'] for h in hits])
        
        c1.metric("TOTAAL VOORDEEL", f"€ {totaal:,.2f}")
        c2.metric("KANSEN", len(hits))
        c3.metric("STATUS", "GELADEN")
        
        if hits:
            st.write("### Gevonden Resultaten")
            res_df = pd.DataFrame(hits)
            res_df['Fiscaal Voordeel'] = res_df['Fiscaal Voordeel'].apply(lambda x: f"€ {x:,.2f}")
            st.table(res_df)
        else:
            st.info("Scan voltooid. Geen investeringen gevonden boven €450.")
    else:
        st.error("Kan data niet lezen. Is dit een geldig exportbestand?")
