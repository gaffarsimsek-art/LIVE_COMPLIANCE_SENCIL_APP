import pandas as pd
import xml.etree.ElementTree as ET

def parse_xaf_auditfile(file_content):
    """Leest een XAF bestand en zet het om naar een lijst met transacties, met extra beveiliging tegen lege velden."""
    try:
        # Gebruik ET.fromstring voor bytes/string content van Streamlit upload
        tree = ET.fromstring(file_content)
        
        # Namespaces in XAF kunnen lastig zijn, we negeren ze voor maximale compatibiliteit
        for el in tree.iter():
            if '}' in el.tag:
                el.tag = el.tag.split('}', 1)[1]
        
        transactions = []
        # Zoek naar alle mutaties (in XAF vaak 'transaction' of 'line')
        entries = tree.findall('.//transaction') + tree.findall('.//line')
        
        for entry in entries:
            # Voorkom 'NoneType' error door .find() resultaat eerst te controleren
            desc_el = entry.find('description')
            desc = desc_el.text if (desc_el is not None and desc_el.text) else "Onbekende omschrijving"
            
            # Zoek naar bedragen, vaak in 'amnt' of 'amount' tags
            amnt_el = entry.find('.//amnt') or entry.find('.//amount')
            try:
                amnt = float(amnt_el.text) if (amnt_el is not None and amnt_el.text) else 0.0
            except ValueError:
                amnt = 0.0
            
            transactions.append({
                'omschrijving': desc,
                'bedrag': amnt
            })
            
        return pd.DataFrame(transactions)
    except Exception as e:
        # Als er echt iets misgaat, geven we een lege lijst terug in plaats van een crash
        return pd.DataFrame(columns=['omschrijving', 'bedrag'])
