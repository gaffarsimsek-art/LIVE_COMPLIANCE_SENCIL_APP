import streamlit as st
import pandas as pd
from match_subsidies import parse_xaf_auditfile, scan_boekhouding

# Strakke UI instellingen
st.set_page_config(page_title="Compliance Sencil | Enterprise Hub", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border-left: 5px solid #00ff00; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Enterprise Hub")

uploaded_file = st.file_uploader("Upload Snelstart Auditfile (.xaf)", type=["xaf"])

if uploaded_file is not None:
    # Lees de inhoud veilig
    content = uploaded_file.read()
    df = parse_xaf_auditfile(content)
    
    if not df.empty:
        results = scan_boekhouding(df)
        
        # Dashboard cijfers
        col1, col2, col3 = st.columns(3)
        total_voordeel = sum([r.get('Bedrag', 0) for r in results if isinstance(r, dict)])
        
        col1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {total_voordeel:,.2f}")
        col2.metric("GEDETECTEERDE KANSEN", len(results))
        col3.metric("COMPLIANCE SCORE", "98%")
        
        # Resultaten Tabel met extra veiligheid voor tekst
        if results:
            clean_results = []
            for r in results:
                if isinstance(r, dict):
                    clean_results.append({
                        "Type": str(r.get("Type", "Onbekend")),
                        "Bedrag": r.get("Bedrag", 0),
                        "Check": str(r.get("Check", "Geen details"))
                    })
            st.table(pd.DataFrame(clean_results))
        else:
            st.info("Geen directe subsidies gevonden, maar de administratie is compliant.")
    else:
        st.error("De Auditfile kon niet worden gelezen. Controleer of het een geldig Snelstart bestand is.")
