from sqlalchemy import Column, Integer, String, Float, Text  # Added Float here
from .database import Base 

class Chemical(Base):
    __tablename__ = "chemicals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cas_number = Column(String, index=True)
    barcode = Column(String, index=True, nullable=True)
    tracking_id = Column(String, unique=True, index=True)
    quantity_value = Column(Float)  # Now Float is defined
    quantity_unit = Column(String)
    hazards = Column(String)        # Fixed spelling (was Strgiing)
    sds_link = Column(String)
    # Force update v3
    