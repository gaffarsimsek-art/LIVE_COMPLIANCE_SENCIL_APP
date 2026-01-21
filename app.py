import streamlit as st
import pandas as pd
import re

def parse_xaf_final(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        # We pakken het hele trLine blok inclusief amntTp (D/C)
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        
        data = []
        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            tp = re.search(r'<amntTp>(.*?)</amntTp>', line) # D of C
            
            if acc and amnt and tp:
                # We pakken alleen DEBET (D) boekingen op Activa rekeningen (<3000)
                # Want een investering is een toename (Debet) op je balans.
                if tp.group(1) == 'D' and acc.group(1).isdigit() and int(acc.group(1)) < 3000:
                    try:
                        val = float(amnt.group(1))
                        if val > 100: # Filter kleine bonnetjes eruit
                            data.append({
                                'rekening': acc.group(1),
                                'omschrijving': desc.group(1) if desc else "Geen omschrijving",
                                'bedrag': val
                            })
                    except: continue
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def scan_kansen(df):
    results = []
    if df.empty: return results
    
    # Verwijder exacte dubbelingen
    df = df.drop_duplicates()
    
    for _, row in df.iterrows():
        d = str(row['omschrijving']).lower()
        b = row['bedrag']
        
        # Brede check voor alles wat op een investering lijkt
        is_invest = any(x in d for x in ['hp', 'comp', 'laptop', 'macbook', 'pc', 'iphone', 'auto', 'mercedes', 'porsche', 'machine', 'meubel', 'inventaris'])
        
        if is_invest or b > 450: # Alles boven 450 op de balans is potentieel KIA
            perc = 0.28
            cat = "KIA (Kleinschaligheid)"
            
            if any(x in d for x in ['elek', 'zon', 'laad', 'milieu']):
                perc = 0.135
                cat = "MIA/EIA (Duurzaam)"
                
            results.append({
                "Categorie": cat,
                "Omschrijving": row['omschrijving'],
                "Bedrag (Ex. BTW)": b,
                "Fiscaal Voordeel": b * perc
            })
    return results

# --- UI ---
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.markdown("<style>.stApp { background-color: #0b0e14; color: white; }</style>", unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Enterprise Hub")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df = parse_xaf_final(file.getvalue())
    if not df.empty:
        hits = scan_kansen(df)
        
        c1, c2, c3 = st.columns(3)
        totaal = sum([h['Fiscaal Voordeel'] for h in hits])
        c1.metric("TOTAAL VOORDEEL", f"€ {totaal:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        c2.metric("GEDETECTEERD", len(hits))
        c3.metric("ANALYSE", "VOLTOOID")
        
        if hits:
            st.write("### 🔍 Gevonden Investeringskansen")
            st.table(pd.DataFrame(hits).style.format({'Bedrag (Ex. BTW)': '€ {:.2f}', 'Fiscaal Voordeel': '€ {:.2f}'}))
        else:
            st.info("Bestand gelezen, maar geen investeringen boven €450 herkend.")
    else:
        st.warning("De scanner kon geen activa-regels vinden in dit bestand.")
