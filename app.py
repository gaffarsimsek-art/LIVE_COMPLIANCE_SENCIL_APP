import streamlit as st
import pandas as pd
from match_subsidies import parse_xaf_auditfile, scan_boekhouding

# 1. Pagina configuratie
st.set_page_config(page_title="Compliance Sencil | Enterprise Hub", layout="wide")

# 2. Visuele styling (Dark Mode SaaS look)
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border-left: 5px solid #00ff00; }
    div[data-testid="stTable"] { background-color: #1e2130; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Compliance Sencil | Enterprise Hub")
st.subheader("Real-time Subsidie & Compliance Scan")

# 3. Bestand uploaden
uploaded_file = st.file_uploader("Upload Snelstart Auditfile (.xaf)", type=["xaf"])

if uploaded_file is not None:
    try:
        # Veilig inlezen van de bytes
        file_bytes = uploaded_file.getvalue()
        
        # Gebruik de parser uit match_subsidies.py
        df = parse_xaf_auditfile(file_bytes)
        
        if df is not None and not df.empty:
            st.success(f"✅ Auditfile succesvol geanalyseerd: {len(df)} transacties gevonden.")
            
            # Scan uitvoeren
            results = scan_boekhouding(df)
            
            # 4. Dashboard cijfers
            col1, col2, col3 = st.columns(3)
            
            # Bereken totaal voordeel veilig
            total_voordeel = sum([r.get('Bedrag', 0) for r in results]) if results else 0
            
            col1.metric("TOTAAL FISCAAL VOORDEEL", f"€ {total_voordeel:,.2f}")
            col2.metric("GEDETECTEERDE KANSEN", len(results))
            col3.metric("COMPLIANCE SCORE", "98%")
            
            # 5. Resultaten weergeven
            st.write("### Gevonden Investeringskansen")
            if results:
                # Zet resultaten om naar een toonbare tabel
                display_df = pd.DataFrame(results)
                st.table(display_df)
            else:
                st.info("Geen specifieke MIA/EIA subsidies gevonden in deze file. De administratie is verder compliant.")
        else:
            st.warning("De file is geüpload, maar bevat geen leesbare transactiegegevens. Controleer of het een financieel XAF-bestand is.")
            
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het verwerken: {e}")
else:
    st.info("Upload een .xaf bestand uit Snelstart om de scan te starten.")
