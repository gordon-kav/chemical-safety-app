from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware  # <--- NEW IMPORT
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
import requests 

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

Base.metadata.create_all(bind=engine)

# --- PYDANTIC MODELS ---
class ChemicalBase(BaseModel):
    name: str
    cas_number: str
    hazards: str
    description: str

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
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{chemical_name}/cids/JSON"
        resp = requests.get(url)
        if resp.status_code != 200:
            return None
        
        cid = resp.json()['IdentifierList']['CID'][0]
        
        details_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=GHS%20Classification"
        resp_details = requests.get(details_url)
        
        if resp_details.status_code == 200:
            full_text = resp_details.text
            hazards = []
            if "H22" in full_text: hazards.append("Flammable")
            if "H30" in full_text: hazards.append("Toxic if swallowed")
            if "H31" in full_text: hazards.append("Skin Irritant")
            if "H35" in full_text: hazards.append("Carcinogenic")
            if "H4" in full_text:  hazards.append("Aquatic Toxicity")
            
            if not hazards: return "Safe / No Data"
            return ", ".join(list(set(hazards)))
            
    except Exception as e:
        print(f"PubChem Error: {e}")
        return None
    return None

# --- APP SETUP ---
app = FastAPI()

# --- SECURITY FIX (CORS) ---
# This tells the backend: "Allow anyone to talk to me"
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
        
    found_hazards = fetch_hazards_from_pubchem(scientific_name)
    
    if found_hazards:
        return {
            "found": True,
            "suggested_name": scientific_name.title(),
            "hazards": found_hazards,
            "description": f"Auto-detected via PubChem search for '{scientific_name}'"
        }
    else:
        return {"found": False}