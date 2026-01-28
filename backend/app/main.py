from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
import requests 
import io
import csv

# --- DATABASE SETUP ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./chemical_inventory.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DATABASE MODEL ---
class Chemical(Base):
    __tablename__ = "chemicals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cas_number = Column(String, unique=True, index=True)
    hazards = Column(String) 
    description = Column(String)
    sds_link = Column(String) # <--- NEW COLUMN

# Create tables (Only works for new tables, won't auto-update existing ones)
Base.metadata.create_all(bind=engine)

# --- PYDANTIC MODELS ---
class ChemicalBase(BaseModel):
    name: str
    cas_number: str
    hazards: str
    description: str
    sds_link: Optional[str] = "" # <--- NEW FIELD

class ChemicalCreate(ChemicalBase):
    pass

class ChemicalResponse(ChemicalBase):
    id: int
    class Config:
        orm_mode = True

# --- THE BRIDGE LOGIC ---
KEYWORD_MAP = {
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
    "drain": "sodium hydroxide",
    "soda": "sodium bicarbonate"
}

def fetch_hazards_from_pubchem(chemical_name: str):
    try:
        # 1. Get CID
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{chemical_name}/cids/JSON"
        resp = requests.get(url)
        if resp.status_code != 200:
            return None
        
        cid = resp.json()['IdentifierList']['CID'][0]
        
        # 2. Generate the Official LCSS (SDS) Link
        # This links to the Safety section of the PubChem page
        sds_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}#section=Safety-and-Hazards"

        # 3. Get Hazards
        details_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=GHS%20Classification"
        resp_details = requests.get(details_url)
        
        hazards = []
        if resp_details.status_code == 200:
            full_text = resp_details.text
            if "H22" in full_text: hazards.append("Flammable")
            if "H30" in full_text: hazards.append("Toxic if swallowed")
            if "H31" in full_text: hazards.append("Skin Irritant")
            if "H35" in full_text: hazards.append("Carcinogenic")
            if "H4" in full_text:  hazards.append("Aquatic Toxicity")
        
        if not hazards: 
            hazards_str = "Safe / No Data"
        else:
            hazards_str = ", ".join(list(set(hazards)))

        return {
            "hazards": hazards_str,
            "sds_link": sds_url
        }
            
    except Exception as e:
        print(f"PubChem Error: {e}")
        return None
    return None

# --- APP SETUP ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROUTES ---

@app.get("/")
def read_root():
    return {"message": "Chemical Safety API is Running!"}

# --- DATABASE REPAIR TOOL (Run once) ---
@app.get("/db-upgrade")
def upgrade_db(db: Session = Depends(get_db)):
    try:
        # This forces the database to add the new 'sds_link' column
        db.execute(text("ALTER TABLE chemicals ADD COLUMN sds_link VARCHAR;"))
        db.commit()
        return {"message": "Database successfully upgraded! 'sds_link' column added."}
    except Exception as e:
        return {"message": "Database likely already upgraded or error occurred.", "details": str(e)}

@app.post("/chemicals/", response_model=ChemicalResponse)
def create_chemical(chemical: ChemicalCreate, db: Session = Depends(get_db)):
    db_chemical = Chemical(**chemical.dict())
    db.add(db_chemical)
    db.commit()
    db.refresh(db_chemical)
    return db_chemical

@app.get("/chemicals/", response_model=List[ChemicalResponse])
def read_chemicals(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    chemicals = db.query(Chemical).offset(skip).limit(limit).all()
    return chemicals

@app.get("/autofill/{query}")
def autofill_data(query: str):
    query = query.lower()
    
    scientific_name = None
    for key, value in KEYWORD_MAP.items():
        if key in query:
            scientific_name = value
            break
    
    if not scientific_name:
        scientific_name = query
        
    data = fetch_hazards_from_pubchem(scientific_name)
    
    if data:
        return {
            "found": True,
            "suggested_name": scientific_name.title(),
            "hazards": data["hazards"],
            "sds_link": data["sds_link"], # <--- Sending the link back
            "description": f"Auto-detected via PubChem search for '{scientific_name}'"
        }
    else:
        return {"found": False}

@app.get("/export_csv")
def export_inventory(db: Session = Depends(get_db)):
    chemicals = db.query(Chemical).all()
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Updated Header to include SDS Link
    writer.writerow(["ID", "Name", "CAS/Barcode", "Hazards", "Description", "SDS Link"])
    
    for c in chemicals:
        # Updated Row to include SDS Link
        writer.writerow([c.id, c.name, c.cas_number, c.hazards, c.description, c.sds_link])
        
    output.seek(0)
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=chemical_inventory.csv"
    return response