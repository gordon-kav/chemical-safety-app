from pydantic import BaseModel
from typing import Optional

# Base schema (shared properties)
class ChemicalBase(BaseModel):
    name: str
    cas_number: str
    barcode: Optional[str] = None  # <--- NEW LINE HERE
    hazards: str
    # ... (keep the rest same)

# Schema for creating a chemical (Frontend sends this)
class ChemicalCreate(ChemicalBase):
    pass

# Schema for reading a chemical (Backend returns this)
class Chemical(ChemicalBase):
    id: int

    class Config:
        from_attributes = True