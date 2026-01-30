from sqlalchemy import Column, Integer, String, Text
# IMPORTANT: Import Base from database.py so main.py can find it later
from .database import Base 

class Chemical(Base):
    __tablename__ = "chemicals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cas_number = Column(String, index=True)
    barcode = Column(String, index=True, nullable=True)  # <--- NEW LINE HERE
    tracking_id = Column(String, unique=True, index=True)
    # ... (keep the rest the same) ...