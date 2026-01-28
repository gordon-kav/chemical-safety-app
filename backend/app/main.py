from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
import requests 
import io
import csv
import uuid 

# --- DATABASE SETUP (Fixed for Render) ---
DATABASE_URL = os.getenv("DATABASE_URL")

# FIX: Render provides "postgres://", but SQLAlchemy needs "postgresql://"
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# FALLBACK: Local testing
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./chemical_inventory.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DATABASE MODELS ---
class Chemical(Base):
    __tablename__ = "chemicals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cas_number = Column(String, index=True) 
    hazards = Column(String) 
    description = Column(String)
    sds_link = Column(String)
    quantity_value = Column(Float)  # e.g. 500.0
    quantity_unit = Column(String)  # e.g. "ml"
    tracking_id = Column(String, unique=True) 

Base.metadata.create_all(bind=engine)

class ChemicalBase(BaseModel):
    name: str
    cas_number: str
    hazards: str
    description: str
    sds_link: Optional[str] = ""
    quantity_value: float 
    quantity_unit: str

class ChemicalCreate(ChemicalBase):
    pass

class ChemicalResponse(ChemicalBase):
    id: int
    tracking_id: Optional[str] = None
    class Config:
        orm_mode = True

# --- BRIDGE LOGIC ---
KEYWORD_MAP = { 
    "bleach": "sodium hypochlorite", 
    "clorox": "sodium hypochlorite", 
    "acetone": "acetone", 
    "ethanol": "ethanol", 
    "methanol": "methanol" 
}

def fetch_hazards_from_pubchem(chemical_name: str):
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{chemical_name}/cids/JSON"
        resp = requests.get(url)
        if resp.status_code != 200: return None
        cid = resp.json()['IdentifierList']['CID'][0]
        sds_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}#section=Safety-and-Hazards"
        details_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=GHS%20Classification"
        resp_details = requests.get(details_url)
        hazards = []
        if resp_details.status_code == 200:
            if "H22" in resp_details.text: hazards.append("Flammable")
            if "H30" in resp_details.text: hazards.append("Toxic")
            if "H31" in resp_details.text: hazards.append("Irritant")
            if "H35" in resp_details.text: hazards.append("Carcinogenic")
            if "H4" in resp_details.text:  hazards.append("Aquatic Hazard")
        return {"hazards": ", ".join(list(set(hazards))) if hazards else "Safe", "sds_link": sds_url}
    except: return None

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- ROUTES ---

@app.get("/")
def read_root():
    return {"message": "Inventory System Online"}

@app.get("/db-upgrade-v3")
def upgrade_db_v3(db: Session = Depends(get_db)):
    msgs = []
    try:
        try: db.execute(text("ALTER TABLE chemicals ADD COLUMN quantity_value FLOAT;")); msgs.append("Added quantity_value")
        except: pass
        try: db.execute(text("ALTER TABLE chemicals ADD COLUMN quantity_unit VARCHAR;")); msgs.append("Added quantity_unit")
        except: pass
        try: db.execute(text("ALTER TABLE chemicals ADD COLUMN tracking_id VARCHAR;")); msgs.append("Added tracking_id")
        except: pass
        try: db.execute(text("DROP INDEX IF EXISTS ix_chemicals_cas_number;")); msgs.append("Allowed duplicate barcodes")
        except: pass
        try: db.execute(text("ALTER TABLE chemicals DROP CONSTRAINT IF EXISTS chemicals_cas_number_key;")); msgs.append("Removed constraint")
        except: pass
        db.commit()
        return {"status": "success", "updates": msgs}
    except Exception as e: return {"error": str(e)}

@app.post("/chemicals/", response_model=ChemicalResponse)
def create_chemical(chemical: ChemicalCreate, db: Session = Depends(get_db)):
    new_chemical = Chemical(
        name=chemical.name,
        cas_number=chemical.cas_number,
        hazards=chemical.hazards,
        description=chemical.description,
        sds_link=chemical.sds_link,
        quantity_value=chemical.quantity_value,
        quantity_unit=chemical.quantity_unit,
        tracking_id=str(uuid.uuid4())[:8]
    )
    db.add(new_chemical)
    db.commit()
    db.refresh(new_chemical)
    return new_chemical

@app.get("/total_stock/{chemical_name}")
def get_total_stock(chemical_name: str, db: Session = Depends(get_db)):
    bottles = db.query(Chemical).filter(Chemical.name.ilike(f"%{chemical_name}%")).all()
    total = 0.0
    unit = "unknown"
    if bottles:
        unit = bottles[0].quantity_unit 
        for b in bottles:
            if b.quantity_unit == unit:
                total += (b.quantity_value or 0)
    return {"chemical": chemical_name, "total_stock": total, "unit": unit, "bottle_count": len(bottles)}

@app.get("/chemicals/", response_model=List[ChemicalResponse])
def read_chemicals(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Chemical).offset(skip).limit(limit).all()

@app.get("/autofill/{query}")
def autofill(query: str):
    q = query.lower()
    name = KEYWORD_MAP.get(q, q)
    data = fetch_hazards_from_pubchem(name)
    if data: return {"found": True, "suggested_name": name.title(), "hazards": data["hazards"], "