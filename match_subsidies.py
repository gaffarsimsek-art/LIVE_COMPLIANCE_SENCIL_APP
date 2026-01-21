import pandas as pd
import xml.etree.ElementTree as ET
import re

def parse_xaf_auditfile(file_content):
    try:
        # Verwerk de XML veilig
        root = ET.fromstring(file_content)
        # Verwijder namespaces
        for el in root.iter():
            if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
        
        data = []
        # Zoek alle transactie-regels
        for line in root.findall('.//trLine'):
            try:
                desc_el = line.find('description')
                desc = desc_el.text if (desc_el is not None and desc_el.text) else "Geen omschrijving"
                
                amnt_el = line.find('amnt')
                amnt = float(amnt_el.text) if (amnt_el is not None and amnt_el.text) else 0.0
                
                data.append({'omschrijving': desc, 'bedrag': amnt})
            except:
                continue # Sla corrupte regels over
        
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame(columns=['omschrijving', 'bedrag'])

def scan_boekhouding(df):
    results = []
    if df.empty: return results
    
    for _, row in df.iterrows():
        # Veilig omschrijving ophalen
        omschr = str(row.get('omschrijving', '')).lower()
        bedrag = row.get('bedrag', 0)
        
        # Check op investeringen (voorbeeld)
        if 'elektr' in omschr or 'zonnepaneel' in omschr:
            results.append({
                "Type": "MIA/EIA Potentieel",
                "Bedrag": bedrag * 0.135,
                "Check": f"Gevonden in: {omschr}"
            })
    return results
