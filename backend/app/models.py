from sqlalchemy import Column, Integer, String, Text
# IMPORTANT: Import Base from database.py so main.py can find it later
from .database import Base 

class Chemical(Base):
    __tablename__ = "chemicals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cas_number = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    hazards = Column(String, nullable=True) # e.g., "Flammable, Corrosive"