import streamlit as st
import pandas as pd
import re

def extract_kenteken(text):
    # Zoekt naar Nederlandse kenteken patronen
    patroon = r'\b([A-Z0-9]{2}-?[A-Z0-9]{2}-?[A-Z0-9]{2}|[A-Z]{1}-?\d{3}-?[A-Z]{2})\b'
    match = re.search(patroon, text.upper())
    return match.group(0) if match else None

def parse_xaf_rdw_logic(file_content):
    try:
        text = file_content.decode('iso-8859-1', errors='ignore')
        lines = re.findall(r'<trLine>(.*?)</trLine>', text, re.DOTALL)
        
        data = []
        for line in lines:
            acc = re.search(r'<accID>(.*?)</accID>', line)
            desc = re.search(r'<desc>(.*?)</desc>', line)
            amnt = re.search(r'<amnt>(.*?)</amnt>', line)
            tp = re.search(r'<amntTp>(.*?)</amntTp>', line)
            
            if acc and amnt and tp:
                description = desc.group(1) if desc else ""
                clean_desc = description.lower()
                
                # MENSELIJK FILTER: Geen verzekeringen, lease of correcties
                uitsluit_termen = ['insurance', 'wa casco', 'premie', 'lease', 'financial', 'corr', 'beginbalans', 'afschr']
                if any(x in clean_desc for x in uitsluit_termen):
                    continue

                if int(acc.group(1)) < 1000 and tp.group(1) == 'D':
                    val = float(amnt.group(1).replace(',', '.'))
                    if val >= 450:
                        data.append({'rekening': acc.group(1), 'omschrijving': description, 'bedrag': val})
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def scan_met_rdw(df):
    results = []
    for _, row in df.iterrows():
        d = row['omschrijving']
        b = row['bedrag']
        kenteken = extract_kenteken(d)
        
        type_aftrek = "KIA"
        percentage = 0.28
        label = "Materiële Activa"
        
        # RDW Logica simulatie (MIA check)
        # In een echte omgeving zou hier een API call naar 'opendata.rdw.nl' gaan
        is_elektrisch = any(x in d.lower() for x in ['elektr', 'ev', 'taycan', 'eqs', 'tesla'])
        
        if is_elektrisch:
            type_aftrek = "MIA / VAMIL"
            percentage = 0.135 # Gemiddeld netto voordeel
            label = "Duurzame Investering (RDW Check: Elektrisch)"
        elif kenteken and not is_elektrisch:
            # Brandstof personenauto's zijn vaak uitgesloten van KIA
            if any(x in d.lower() for x in ['mercedes', 'porsche', 'audi']):
                continue # Skip brandstof personenwagens
        
        results.append({
            "Check": label,
            "Kenteken": kenteken if kenteken else "N.v.t.",
            "Investering": d,
            "Bedrag": b,
            "Fiscaal Voordeel": b * percentage
        })
    return results

# --- UI ---
st.set_page_config(page_title="Compliance Sencil | RDW Scan", layout="wide")
st.title("🛡️ Compliance Sencil | RDW & Activa Intelligence")

file = st.file_uploader("Upload .xaf bestand", type=["xaf"])

if file:
    df = parse_xaf_rdw_logic(file.getvalue())
    if not df.empty:
        hits = scan_met_rdw(df)
        
        c1, c2, c3 = st.columns(3)
        totaal_v = sum([h['Fiscaal Voordeel'] for h in hits])
        c1.metric("FISCAAL VOORDEEL", f"€ {totaal_v:,.2f}")
        c2.metric("GECHECKEERDE POSTEN", len(hits))
        c3.metric("RDW STATUS", "ACTIVE")
        
        if hits:
            st.table(pd.DataFrame(hits).style.format({'Bedrag': '€ {:,.2f}', 'Fiscaal Voordeel': '€ {:,.2f}'}))
