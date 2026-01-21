def scan_voor_subsidies(df):
    results = []
    if df.empty: return results
    
    # We filteren op unieke omschrijvingen om dubbele boekingen (Debet/Credit) te voorkomen
    df_unique = df.drop_duplicates(subset=['omschrijving', 'bedrag'])

    for _, row in df_unique.iterrows():
        desc = str(row['omschrijving']).lower()
        acc = str(row['rekening'])
        bedrag = row['bedrag']

        # 1. Herkenning van de HP Computer uit Ave Export (Rekening 100 = Inventaris)
        # We voegen '100' specifiek toe omdat Snelstart dit vaak gebruikt
        is_inventaris = acc in ['100', '110', '120', '0100', '0110', '0120']
        
        # 2. Trefwoorden voor MIA/EIA/KIA
        subsidie_terms = ['elektr', 'zonne', 'laad', 'warmtepomp', 'accu', 'isolatie']
        kia_terms = ['hp', 'computer', 'laptop', 'pc', 'machine', 'server', 'monitor']

        if any(t in desc for t in subsidie_terms) and bedrag > 2500:
            results.append({
                "Type": "MIA/EIA Potentieel",
                "Item": row['omschrijving'],
                "Bedrag": bedrag,
                "Voordeel": bedrag * 0.135
            })
        elif is_inventaris or any(t in desc for t in kia_terms):
            if bedrag >= 450 and bedrag < 50000: # Filter voor reële MKB investeringen
                results.append({
                    "Type": "KIA Potentieel (Aftrek)",
                    "Item": row['omschrijving'],
                    "Bedrag": bedrag,
                    "Voordeel": bedrag * 0.28 # De fiscale aftrekpost
                })

    return results
