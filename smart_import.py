import requests
import time

# --- CONFIGURATION ---
API_URL = "https://chemical-safety-app.onrender.com"

# YOUR GOOGLE SHEET URL
INPUT_SOURCE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR30oLbA47zoW07S01Rjcy2fsPWzY3RyF2IBZZHRdD6_SlU1iKHW01nljx5YilM7tNJi5wAvmHnV5Zk/pub?output=csv"

def get_lines_from_source(source):
    """Reads lines from a local file OR a web URL"""
    try:
        if source.startswith("http"):
            print(f"☁️ Downloading list from Google Sheets...")
            resp = requests.get(source)
            resp.raise_for_status() # Check for download errors
            return resp.text.splitlines()
        else:
            print(f"📂 Reading local file: {source}...")
            with open(source, 'r') as f:
                return f.readlines()
    except Exception as e:
        print(f"❌ Error reading source: {e}")
        return []

def fetch_details_from_pubchem(identifier):
    """Asks PubChem for details on a CAS number or Name"""
    try:
        # 1. Get the CID (Compound ID)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{identifier}/cids/JSON"
        resp = requests.get(url)
        if resp.status_code != 200: return None
        
        cid = resp.json()['IdentifierList']['CID'][0]
        
        # 2. Get the Name and GHS Data
        details_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=GHS%20Classification"
        resp_details = requests.get(details_url)
        
        # 3. Get proper name
        name_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/Title/JSON"
        name_resp = requests.get(name_url)
        official_name = name_resp.json()['PropertyTable']['Properties'][0]['Title']

        # 4. Parse Hazards
        hazards = []
        if resp_details.status_code == 200:
            text_data = resp_details.text
            if "H22" in text_data: hazards.append("Flammable")
            if "H30" in text_data: hazards.append("Toxic")
            if "H31" in text_data: hazards.append("Irritant")
            if "H35" in text_data: hazards.append("Carcinogenic")
            if "H314" in text_data: hazards.append("Corrosive")
            if "H4" in text_data:  hazards.append("Aquatic Hazard")
        
        hazard_str = ", ".join(list(set(hazards))) if hazards else "Check SDS"
        sds_link = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}#section=Safety-and-Hazards"

        return {
            "name": official_name,
            "cas_number": identifier,
            "hazards": hazard_str,
            "sds_link": sds_link
        }
    except Exception as e:
        # print(f"Debug: {e}") # Uncomment if you want to see specific errors
        return None

def run_smart_import():
    lines = get_lines_from_source(INPUT_SOURCE)
    
    if not lines:
        print("❌ No data found in the spreadsheet.")
        return

    print(f"📋 Found {len(lines)} rows to process.")
    print("------------------------------------------------")

    for line in lines:
        # Google Sheets CSVs separate columns with commas.
        # We assume the CAS NUMBER / NAME is in the FIRST COLUMN.
        item = line.strip().split(",")[0]
        
        # Clean up quotes (Google sometimes wraps text in quotes)
        item = item.replace('"', '').strip()

        # Skip headers or empty lines
        if not item or item.lower() in ["name", "cas", "cas_number", "chemical"]: 
            continue 

        print(f"🔍 Looking up: {item}...")
        
        # 1. Ask PubChem for data
        data = fetch_details_from_pubchem(item)
        
        if data:
            # 2. Add default inventory fields
            payload = {
                "name": data['name'],
                "cas_number": data['cas_number'],
                "hazards": data['hazards'],
                "description": "Cloud Import",
                "sds_link": data['sds_link'],
                "quantity_value": 0.0,    # Default to 0 (Reference Item)
                "quantity_unit": "ml"
            }

            # 3. Send to your App
            try:
                response = requests.post(f"{API_URL}/chemicals/", json=payload)
                if response.status_code == 200:
                    print(f"   ✅ Success: Added {data['name']}")
                else:
                    print(f"   ❌ Database Error: {response.text}")
            except Exception as e:
                print(f"   ❌ Connection Error: {e}")
        else:
            print(f"   ⚠️ Not found in PubChem (Check spelling/CAS)")
        
        # Be polite to the API (prevent blocking)
        time.sleep(0.5)

    print("------------------------------------------------")
    print("✨ Import Complete!")

if __name__ == "__main__":
    run_smart_import()