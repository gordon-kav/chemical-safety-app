from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import csv
import io
from fastapi.responses import StreamingResponse
from typing import Listimport os
import sys

# --- DEBUGGING PRINT ---
print("--------------------------------------------------")
print("DEBUG CHECK STARTING")
db_url = os.getenv("DATABASE_URL")
print(f"DEBUG: DATABASE_URL is: {db_url}")
if not db_url:
    print("DEBUG: ALERT! The variable is MISSING. Using SQLite.")
else:
    print("DEBUG: Variable found. Connecting to Postgres.")
print("--------------------------------------------------")
# -----------------------


# Import your database and models
from .database import engine, SessionLocal
from . import models, schemas

# Create the database tables (This ensures tables exist)
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- CORS (Security) ---
# This allows your frontend (and yourself) to talk to this backend
origins = ["*"]  # "Allow everyone" - simplest for your setup

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency to get Database Connection ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Routes ---

@app.get("/")
def read_root():
    return {"message": "Chemical Safety API is Live"}

@app.get("/chemicals", response_model=List[schemas.Chemical])
def read_chemicals(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    chemicals = db.query(models.Chemical).offset(skip).limit(limit).all()
    return chemicals

@app.post("/chemicals", response_model=schemas.Chemical)
def create_chemical(chemical: schemas.ChemicalCreate, db: Session = Depends(get_db)):
    # Check if tracking_id already exists to prevent duplicates
    db_chemical = db.query(models.Chemical).filter(models.Chemical.tracking_id == chemical.tracking_id).first()
    if db_chemical:
        raise HTTPException(status_code=400, detail="Tracking ID already registered")
    
    # Create the new chemical entry
    new_chemical = models.Chemical(
        name=chemical.name,
        cas_number=chemical.cas_number,
        barcode=getattr(chemical, "barcode", None), # Safety check for input
        tracking_id=chemical.tracking_id,
        quantity_value=chemical.quantity_value,
        quantity_unit=chemical.quantity_unit,
        hazards=chemical.hazards,
        sds_link=chemical.sds_link
    )
    db.add(new_chemical)
    db.commit()
    db.refresh(new_chemical)
    return new_chemical

@app.get("/search", response_model=List[schemas.Chemical])
def search_chemicals(q: str, db: Session = Depends(get_db)):
    # Search by Name, CAS Number, or Barcode
    results = db.query(models.Chemical).filter(
        (models.Chemical.name.ilike(f"%{q}%")) | 
        (models.Chemical.cas_number.ilike(f"%{q}%")) |
        (models.Chemical.barcode.ilike(f"%{q}%"))
    ).all()
    return results

@app.get("/export_csv")
def export_csv(db: Session = Depends(get_db)):
    chemicals = db.query(models.Chemical).all()
    
    # Create an in-memory file
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write the Header Row
    writer.writerow([
        "ID", 
        "Name", 
        "CAS Number", 
        "Barcode", 
        "Tracking ID", 
        "Quantity", 
        "Unit", 
        "Hazards", 
        "SDS Link"
    ])
    
    # Write the Data Rows
    for c in chemicals:
        writer.writerow([
            c.id,
            c.name,
            c.cas_number,
            # SAFETY VALVE: This checks if 'barcode' exists. 
            # If it's missing, it inserts an empty string instead of crashing.
            getattr(c, "barcode", ""), 
            c.tracking_id,
            c.quantity_value,
            c.quantity_unit,
            c.hazards,
            c.sds_link
        ])
        
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory.csv"}
    )