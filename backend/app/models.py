from sqlalchemy import Column, Integer, String, Text
# IMPORTANT: Import Base from database.py so main.py can find it later
from .database import Base 

class Chemical(Base):
    __tablename__ = "chemicals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cas_number = Column(String, index=True)
    barcode = Column(String, index=True, nullable=True)  # <--- MAKE SURE THIS LINE IS HERE
    tracking_id = Column(String, unique=True, index=True)
    quantity_value = Column(Float)
    quantity_unit = Column(String)
    hazards = Column(String)
    sds_link = Column(String)