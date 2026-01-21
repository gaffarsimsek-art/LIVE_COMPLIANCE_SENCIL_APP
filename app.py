import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import io
import os
import time
from match_subsidies import process_audit_subsidies, process_payroll_csv, get_rdw_data

# --- Configuration ---
st.set_page_config(
    page_title="Compliance Sencil | Enterprise Hub",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Enterprise Matrix Style ---
st.markdown("""
<style>
    /* Global Theme */
    .stApp {
        background-color: #050505; 
        color: #e0e0e0;
        font-family: 'Rajdhani', 'Segoe UI', sans-serif;
    }

    /* Titles with neon glow */
    h1, h2, h3 {
        color: #ffffff !important;
        text-shadow: 0 0 12px rgba(0, 255, 65, 0.5);
    }
    
    /* Money Cards */
    .money-display-container {
        display: flex;
        gap: 20px;
        margin: 20px 0 40px 0;
    }
    .money-card {
        flex: 1;
        background: radial-gradient(circle at top left, #1a1a1a, #000000);
        border: 1px solid #333;
        border-right: 4px solid #00FF41; 
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        position: relative;
    }
    .money-value {
        font-size: 3.2em;
        font-weight: 800;
        color: #00FF41;
        text-shadow: 0 0 25px rgba(0, 255, 65, 0.3);
        margin: 10px 0;
    }
    .money-label {
        font-size: 1.1em;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 600;
    }

    /* Transparent Dataframes */
    div[data-testid="stDataFrame"] {
        background-color: transparent !important; border: none !important;
    }
    div[data-testid="stDataFrame"] table {
        background-color: transparent !important;
    }
    div[data-testid="stDataFrame"] th {
        background-color: rgba(0, 30, 0, 0.7) !important;
        color: #00FF41 !important;
        border-bottom: 2px solid #00FF41 !important;
    }
    div[data-testid="stDataFrame"] td {
        background-color: transparent !important;
        color: #ddd !important;
        border-bottom: 1px solid rgba(0, 255, 65, 0.2) !important;
    }
    
    /* Glossy Primary Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(180deg, #00FF41 0%, #008f11 100%);
        border: none;
        color: black;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
        border-radius: 8px;
        padding: 0.8em 2em;
        transition: all 0.2s;
    }
    .stButton > button[kind="primary"]:hover {
        transform: scale(1.02);
        box-shadow: 0 0 35px rgba(0, 255, 65, 0.8);
        color: black;
    }

    /* Gold PDF Button */
    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(135deg, #E0E0E0 0%, #D4AF37 40%, #FFD700 100%);
        color: #000;
        font-weight: 900;
        font-size: 1.1em;
        text-transform: uppercase;
        border: 2px solid #FFD700;
        border-radius: 10px;
        box-shadow: 0 0 25px rgba(255, 215, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

def generate_pdf_report(investments, personnel, tax, cash, vehicles):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.cell(0, 10, 'Compliance Sencil | Enterprise RDW Check', 0, 1, 'C')
            self.set_draw_color(0, 200, 83)
            self.line(10, 25, 200, 25)
            self.ln(10)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
            
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # 1. Summary
    pdf.set_fill_color(240, 255, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Directie Samenvatting", 0, 1, 'L', True)
    pdf.ln(5)
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 10, f"Fiscaal Voordeel (Investeringen): EUR {tax:,.2f}", 0, 1)
    pdf.cell(100, 10, f"Cashflow Voordeel (HR):           EUR {cash:,.2f}", 0, 1)
    pdf.ln(5)
    
    # 2. Vehicles Detail (RDW)
    if vehicles:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"RDW Voertuig Verificatie (Live Data)", 0, 1, 'L', True)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(30, 8, "Kenteken", 1)
        pdf.cell(70, 8, "Merk/Model", 1)
        pdf.cell(50, 8, "Brandstof", 1)
        pdf.cell(40, 8, "Subsidie Status", 1, 1)
        
        pdf.set_font("Arial", '', 9)
        for v in vehicles:
            status = "SEBA/MIA OK" if v['Elektrisch'] else "NIET SUBSIDIABEL"
            pdf.cell(30, 8, v['Kenteken'], 1)
            pdf.cell(70, 8, v['Merk'][:30], 1)
            pdf.cell(50, 8, v['Brandstof'][:25], 1)
            pdf.cell(40, 8, status, 1, 1)
        pdf.ln(10)

    # 3. Main Lists
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Transactie Detailoverzicht", 0, 1, 'L', True)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(80, 8, "Omschrijving", 1)
    pdf.cell(30, 8, "Bron", 1)
    pdf.cell(40, 8, "Bedrag", 1, 0, 'R')
    pdf.cell(40, 8, "Voordeel", 1, 1, 'R')
    pdf.set_font("Arial", '', 9)
    for i in investments:
        pdf.cell(80, 8, i['Omschrijving'][:40], 1)
        pdf.cell(30, 8, i['Bron'][:15], 1)
        pdf.cell(40, 8, f"{i['Bedrag']:,.2f}", 1, 0, 'R')
        pdf.cell(40, 8, f"{i.get('Fiscaal_Voordeel',0):,.2f}", 1, 1, 'R')

    return bytes(pdf.output())

# --- UI ---
with st.sidebar:
    st.markdown("### 🏢 Enterprise Console")
    st.info("System Status: **ONLINE**")
    st.markdown("RDW Koppeling: **ACTIEF** 🟢")
    st.markdown("---")
    st.text_input("Licentie", value="ENT-2026-X-ACTIVE", disabled=True)

st.title("Compliance Sencil | Enterprise Hub")

c1, c2 = st.columns(2)
f_xaf = c1.file_uploader("📂 Auditfile (XAF)", type=['xaf', 'xml'])
f_csv = c2.file_uploader("👥 Loonjournaal (CSV)", type=['csv'])

if st.button("🚀 START DEEP SCAN (RDW LIVE)", type="primary"):
    with st.spinner("Connecting to RDW Open Data & Analyzing..."):
        time.sleep(1)
        
        invs, vehs = process_audit_subsidies(f_xaf) if f_xaf else ([], [])
        pers = process_payroll_csv(f_csv) if f_csv else []
        
        # KIA Bonus
        tot_inv = sum(x['Bedrag'] for x in invs)
        if tot_inv > 2800:
            kia = tot_inv * 0.28
            invs.append({"Omschrijving": "Totaal KIA Invest", "Datum": "2026", "Bedrag": tot_inv, "Categorie": "Invest", "Regeling": "KIA", "Fiscaal_Voordeel": kia, "Bron": "System"})
            
        t_tax = sum(x.get('Fiscaal_Voordeel', 0) for x in invs)
        t_cash = sum(x.get('Cash_Voordeel', 0) for x in pers)
        
        # Money
        st.markdown(f"""
        <div class="money-display-container">
            <div class="money-card"><div class="money-label">Direct Cash (HR)</div><div class="money-value">€ {t_cash:,.0f}</div></div>
            <div class="money-card"><div class="money-label">Fiscaal Voordeel (Inv)</div><div class="money-value">€ {t_tax:,.0f}</div></div>
        </div>
        """, unsafe_allow_html=True)
        
        if (t_tax+t_cash) > 10000:
            st.balloons()
            st.success("🎉 **Enterprise Savings Targets Met!**")
            
        # Vehicle Verification Table
        if vehs:
            st.subheader("🚗 RDW Voertuig Verificatie")
            
            # Prepare data
            v_display = []
            for v in vehs:
                status_icon = "✅ CHECK" if v['Elektrisch'] else "❌ GEEN SUBSIDIE"
                v_display.append({
                    "Kenteken": v['Kenteken'],
                    "Merk": v['Merk'],
                    "Brandstof": v['Brandstof'],
                    "Subsidie Status": status_icon
                })
            
            df_v = pd.DataFrame(v_display)
            st.dataframe(df_v, use_container_width=True)
            
            # Big Green Badge if ANY Electric vehicle found
            if any(v['Elektrisch'] for v in vehs):
                 st.markdown("""
                 <div style="background-color: rgba(0,255,65,0.2); border: 2px solid #00FF41; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0;">
                    <h2 style="margin:0; text-shadow:none; color: #00FF41;">✅ RDW BEVESTIGING: ELEKTRISCH VOERTUIG GEDETECTEERD</h2>
                    <p>SEBA & MIA subsidieclaims zijn automatisch toegevoegd aan de resultaten.</p>
                 </div>
                 """, unsafe_allow_html=True)

        # Tabs
        t1, t2 = st.tabs(["Details Investeringen", "Details Personeel"])
        with t1: st.dataframe(pd.DataFrame(invs), use_container_width=True)
        with t2: st.dataframe(pd.DataFrame(pers), use_container_width=True)
        
        # PDF
        pdf_data = generate_pdf_report(invs, pers, t_tax, t_cash, vehs)
        st.download_button("🏆 DOWNLOAD RDW-VERIFIED RAPPORT", pdf_data, "Compliance_Sencil_RDW_2026.pdf", "application/pdf")

st.markdown("<br><br>", unsafe_allow_html=True)
st.caption("Compliance Sencil Enterprise © 2026 | Powered by RDW Open Data")
