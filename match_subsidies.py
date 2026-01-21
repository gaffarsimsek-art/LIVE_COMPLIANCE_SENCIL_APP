import pandas as pd
import xml.etree.ElementTree as ET

def parse_xaf_auditfile(file_content):
    """Leest een XAF bestand en zet het om naar een lijst met transacties, met foutafhandeling."""
    try:
        tree = ET.fromstring(file_content)
        # Verwijder de namespace voor makkelijker zoeken
        for el in tree.iter():
            if '}' in el.tag:
                el.tag = el.tag.split('}', 1)[1]
        
        transactions = []
        for entry in tree.findall('.//transaction'):
            # Gebruik .get() of check op None om de 'NoneType' error te voorkomen
            description_el = entry.find('description')
            desc = description_el.text if description_el is not None else "Geen omschrijving"
            
            amount_el = entry.find('.//amnt')
            amnt = float(amount_el.text) if amount_el is not None and amount_el.text else 0.0
            
            transactions.append({
                'omschrijving': desc,
                'bedrag': amnt
            })
        return pd.DataFrame(transactions)
    except Exception as e:
        print(f"Fout bij lezen XAF: {e}")
        return pd.DataFrame(columns=['omschrijving', 'bedrag'])

# De rest van je bestaande functies (check_rdw_kenteken, etc.) hieronder laten staan...
