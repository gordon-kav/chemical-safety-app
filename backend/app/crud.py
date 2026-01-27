from sqlalchemy.orm import Session
from . import models, schemas

# Function to read a single chemical by ID
def get_chemical(db: Session, chemical_id: int):
    return db.query(models.Chemical).filter(models.Chemical.id == chemical_id).first()

# Function to read a list of chemicals (for the GET request)
def get_chemicals(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Chemical).offset(skip).limit(limit).all()

# Function to create a chemical (This is the one main.py was looking for!)
def create_chemical(db: Session, chemical: schemas.ChemicalCreate):
    # 1. Create the database model instance
    db_chemical = models.Chemical(
        name=chemical.name,
        cas_number=chemical.cas_number,
        description=chemical.description,
        hazards=chemical.hazards
    )
    # 2. Add it to the session
    db.add(db_chemical)
    # 3. Commit (save) the transaction
    db.commit()
    # 4. Refresh to get the generated ID back
    db.refresh(db_chemical)
    return db_chemical