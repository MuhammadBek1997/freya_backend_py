from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class Service(BaseModel):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    duration = Column(Integer, nullable=False)  # in minutes
    is_active = Column(Boolean, default=True)
    
    # Relationships
    salon = relationship("Salon", back_populates="services")