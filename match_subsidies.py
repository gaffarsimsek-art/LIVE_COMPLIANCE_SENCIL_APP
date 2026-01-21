import re
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

# --- RDW & Intelligence Logic ---

def get_rdw_data(license_plate_raw):
    """
    Check RDW API for vehicle details.
    """
    clean_plate = re.sub(r'[^A-Z0-9]', '', license_plate_raw.upper())
    
    brand_str = "Onbekend"
    is_electric = False
    fuel_list = []
    
    try:
        # 1. Main Info
        url_main = f"https://opendata.rdw.nl/resource/m9d7-ebf2.json?kenteken={clean_plate}"
        resp_main = requests.get(url_main, timeout=2)
        if resp_main.status_code == 200:
            data = resp_main.json()
            if data:
                veh = data[0]
                merk = veh.get('merk', '').strip()
                model = veh.get('handelsbenaming', '').strip()
                brand_str = f"{merk} {model}"
        
        # 2. Fuel Info - Crucial for Subsidy
        url_fuel = f"https://opendata.rdw.nl/resource/8ys7-d773.json?kenteken={clean_plate}"
        resp_fuel = requests.get(url_fuel, timeout=2)
        if resp_fuel.status_code == 200:
            data = resp_fuel.json()
            for rec in data:
                fuel_desc = rec.get('brandstof_omschrijving', '').title()
                fuel_list.append(fuel_desc)
                if 'Elektriciteit' in fuel_desc:
                    is_electric = True

    except Exception as e:
        pass 
        
    return brand_str, is_electric, ", ".join(fuel_list)

def find_license_plate(text):
    # Matches common Dutch patterns including dashes
    patterns = [
        r'[A-Za-z]{2}-\d{3}-[A-Za-z]', 
        r'\d-[A-Za-z]{3}-\d{2}',    
        r'\d{2}-[A-Za-z]{3}-\d',    
        r'[A-Za-z]-\d{3}-[A-Za-z]{2}', 
        r'[A-Za-z]{3}-\d{2}-[A-Za-z]', 
        r'\d-[A-Za-z]{2}-\d{3}',    
        r'[A-Za-z]{2}-\d{2}-\d{2}', 
        r'\d{2}-\d{2}-[A-Za-z]{2}',
        r'\d{2}-[A-Za-z]{2}-\d{2}',
        r'[A-Za-z]{2}-\d{2}-[A-Za-z]{2}',
        r'[A-Za-z]{2}-[A-Za-z]{2}-\d{2}',
        r'\d{2}-[A-Za-z]{2}-[A-Za-z]{2}'
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(0).upper()
    return None

def process_audit_subsidies(file):
    transactions = []
    vehicles_found = []
    
    try:
        tree = ET.parse(file)
        root = tree.getroot()
        for elem in root.iter():
            if '}' in elem.tag: elem.tag = elem.tag.split('}', 1)[1]
                
        for transaction in root.iter('transaction'):
            desc = transaction.find('desc').text or ""
            date = transaction.find('date').text or ""
            for trLine in transaction.findall('trLine'):
                try: amnt = float(trLine.find('amnt').text)
                except: amnt = 0.0
                
                if abs(amnt) > 450:
                    regeling, benefit = None, 0.0
                    source_info = "Grootboek"
                    
                    # RDW Check first
                    plate = find_license_plate(desc)
                    if plate:
                        brand, is_ev, fuel_str = get_rdw_data(plate)
                        
                        veh_info = {
                            "Kenteken": plate,
                            "Merk": brand,
                            "Brandstof": fuel_str,
                            "Elektrisch": is_ev,
                        }
                        vehicles_found.append(veh_info)
                        
                        if is_ev:
                            # SEBA + MIA 
                            # SEBA = 5000 max (simplified)
                            # MIA = 36% of Invest * 25.8% VPB
                            seba_amt = 5000.00
                            mia_benefit = abs(amnt) * 0.36 * 0.258
                            
                            regeling = "SEBA (Subsidie) + MIA"
                            benefit = seba_amt + mia_benefit
                            source_info = f"RDW Bevestigd: {plate}"
                        else:
                            regeling = f"Geen Subsidie ({fuel_str})"
                            benefit = 0.0
                            source_info = f"RDW: {plate}"
                            
                    else:
                        # Fallback Keyword scan
                        d_low = desc.lower()
                        if "warmtepomp" in d_low or "zonnepaneel" in d_low:
                            regeling = "EIA (Energie)"
                            benefit = abs(amnt) * 0.40 * 0.258
                        elif "investering" in d_low:
                            regeling = "KIA Potentieel"
                            benefit = 0.0
                    
                    if regeling:
                        transactions.append({
                            "Omschrijving": desc,
                            "Datum": date,
                            "Bedrag": abs(amnt),
                            "Categorie": "Investering",
                            "Regeling": regeling,
                            "Fiscaal_Voordeel": benefit,
                            "Bron": source_info
                        })
                        
    except Exception as e:
        st.error(f"Error: {e}")
        
    return transactions, vehicles_found

def process_payroll_csv(file):
    results = []
    try:
        df = pd.read_csv(file)
        df.columns = [c.strip() for c in df.columns]
        for _, row in df.iterrows():
            wage = float(row.get('Uurloon', 0))
            age = int(row.get('Leeftijd', 0))
            name = str(row.get('Naam', 'Onbekend'))
            anon_name = f"{name.split(' ')[0][0]}. {name.split(' ')[-1]}"
            
            if age >= 56:
                results.append({
                    "Omschrijving": f"LKV (56+): {anon_name}",
                    "Datum": "2026",
                    "Bedrag": 0, "Categorie": "Personeel", "Regeling": "LKV",
                    "Fiscaal_Voordeel": 0.0, "Cash_Voordeel": 6000.00, "Bron": "HR"
                })
            elif 15.00 <= wage <= 18.00:
                results.append({
                    "Omschrijving": f"LIV: {anon_name}",
                    "Datum": "2026",
                    "Bedrag": 0, "Categorie": "Personeel", "Regeling": "LIV",
                    "Fiscaal_Voordeel": 0.0, "Cash_Voordeel": 1000.00, "Bron": "HR"
                })
    except: pass
    return results