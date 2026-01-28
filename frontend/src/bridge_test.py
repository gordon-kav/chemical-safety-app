import requests
import json
import time

# --- THE "BRAIN" (Fuzzy Matcher) ---
# This is where we map common store words to scientific names
# You can expand this list over time!
keyword_map = {
    "bleach": "sodium hypochlorite",
    "clorox": "sodium hypochlorite",
    "domestos": "sodium hypochlorite",
    "acetone": "acetone",
    "polish remover": "acetone",
    "spirit": "mineral spirits",
    "turpentine": "turpentine",
    "ethanol": "ethanol",
    "alcohol": "ethanol",
    "methanol": "methanol",
    "drain": "sodium hydroxide", # Drain cleaners are usually this
    "soda": "sodium bicarbonate"
}

def get_pubchem_data(chemical_name):
    """
    Asks the National Institutes of Health (PubChem) for safety data.
    """
    print(f"   🔎 Searching PubChem for: '{chemical_name}'...")
    
    # 1. Search for the chemical ID (CID)
    search_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{chemical_name}/cids/JSON"
    try:
        response = requests.get(search_url)
        if response.status_code != 200:
            print("   ❌ PubChem didn't recognize that name.")
            return None
            
        data = response.json()
        cid = data['IdentifierList']['CID'][0] # Get the first result
        print(f"   ✅ Found PubChem ID: {cid}")
        
        # 2. Get the Safety Data (GHS Hazards) for that ID
        # Note: This is a complex query to their 'Safety' view
        details_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=GHS%20Classification"
        
        resp_details = requests.get(details_url)
        if resp_details.status_code == 200:
            # We have to dig deep into the JSON to find the "H-Statements" (Hazard Statements)
            # This logic parses their specific tree structure
            full_text = resp_details.text
            
            # Quick hack to extract H-codes (e.g., H225) without parsing the whole massive tree
            hazards = []
            if "H22" in full_text: hazards.append("Flammable")
            if "H30" in full_text: hazards.append("Toxic if swallowed")
            if "H31" in full_text: hazards.append("Skin Irritant/Corrosive")
            if "H35" in full_text: hazards.append("Carcinogenic")
            if "H4" in full_text:  hazards.append("Aquatic Toxicity")
            
            return list(set(hazards)) # Remove duplicates
            
    except Exception as e:
        print(f"   ⚠️ Error connecting to PubChem: {e}")
        return None

def main():
    print("--- 🌉 CHEMICAL BRIDGE PROTOTYPE ---")
    print("Simulating the connection between Product Names and Safety Data")
    
    while True:
        print("\n" + "="*40)
        product_name = input("Enter a Product Name (e.g., 'Clorox Bleach', 'Nail Polish Remover'): ").lower()
        
        if product_name == "exit":
            break

        # --- STEP 1: THE CLEANER ---
        # Look for keywords in the product name
        scientific_name = None
        for key, value in keyword_map.items():
            if key in product_name:
                scientific_name = value
                print(f"   🔄 Translated '{product_name}' -> '{scientific_name}'")
                break
        
        if not scientific_name:
            print("   ⚠️  Could not guess the chemical from that name.")
            print("   (Try adding more keywords to the 'keyword_map' in the script!)")
            continue

        # --- STEP 2: THE FETCHER ---
        hazards = get_pubchem_data(scientific_name)
        
        if hazards:
            print(f"\n   🎯 RESULT for {scientific_name.upper()}:")
            if len(hazards) == 0:
                print("   Safe / No GHS Hazards found.")
            else:
                for h in hazards:
                    print(f"   ⚠️  {h}")
        
        time.sleep(1)

if __name__ == "__main__":
    main()