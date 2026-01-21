import streamlit as st
import pandas as pd
import re

def parse_xaf_final(file_content):
    try:
        text = file_content.decode('latin-1', errors='ignore')
        
        # We zoeken naar de dagboeken om te zien wat de beginbalans is
        # Vaak gemarkeerd met <jrnID> of in een sectie <openingBalance>
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        
        extracted_data = []
        for line in lines:
            # Check of dit een beginbalans regel is (Snelstart gebruikt vaak dagboek '000' of '999')
            # Of we kijken naar de omschrijving 'Beginbalans'
            desc_match = re.search(r'<desc>(.*?)</desc>', line)
            desc = desc_match.group(1) if desc_match else ""
            
            if "beginbalans" in desc.lower() or "openingsbalans" in desc.lower():
                continue # Sla deze regel over!

            acc = re.search(r'<accID>(.*?)</accID>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            
            if acc and amnt:
                try:
                    num_val = abs(float(amnt.group(1).replace(',', '.')))
                    if num_val > 0:
                        extracted_data.append({
                            'rekening': acc.group(1),
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
    
    # Unieke omschrijvingen om dubbelingen (Debet/Credit) te voorkomen
    df = df.drop_duplicates(subset=['omschrijving', 'bedrag'])
    
    for _, row in df.iterrows():
        d = str(row['omschrijving']).lower()
        a = str(row['rekening'])
        b = row['bedrag']
        
        # KIA Check: Alleen nieuwe investeringen (geen beginbalans meer)
        # Rekening 100-199 is vaak inventaris bij Snelstart
        is_inventaris = (a.isdigit() and 100 <= int(a) <= 199)
        trefwoorden = ['hp ', 'computer', 'laptop', 'macbook', 'machine', 'inventaris']

        if (is_inventaris or any(x in d for x in trefwoorden)) and b >= 450:
            results.append({
                "Type": "KIA (Investeringsaftrek)",
                "Item": row['omschrijving'],
                "Investering": b,
                "Fiscaal Voordeel": b * 0.28
            })
            
    return results

# UI instellingen blijven gelijk...
st.set_page_config(page_title="Compliance Sencil", layout="wide")
st.markdown("<style>.stApp { background-color: #0b0e14; color: white; }</style>", unsafe_allow_html=True)
st.title("🛡️ Compliance Sencil | Enterprise Hub")

file = st.file_uploader("Upload Snelstart Auditfile (.xaf)", type=["xaf"])

if file:
    df = parse_xaf_final(file.getvalue())
    if not df.empty:
        hits = analyseer_subsidies(df)
        c1, c2, c3 = st.columns(3)
        totaal = sum([h['Fiscaal Voordeel'] for h in hits])
        c1.metric("TOTAAL VOORDEEL 2024", f"€ {totaal:,.2f}")
        c2.metric("NIEUWE KANSEN", len(hits))
        c3.metric("STATUS", "GEZUIVERD VAN BEGINBALANS")
        
        if hits:
            st.write("### 🔍 Nieuwe Investeringen Gedetecteerd")
            st.table(pd.DataFrame(hits))
        else:
            st.info("Geen nieuwe investeringen gevonden. (Beginbalans is genegeerd)")
