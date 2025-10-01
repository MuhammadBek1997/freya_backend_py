from sqlalchemy import Column, String, Boolean, Text, Integer, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class Salon(BaseModel):
    __tablename__ = "salons"
    
    salon_logo = Column(String(255))
    salon_name = Column(String(200), nullable=False)
    salon_phone = Column(String(20))
    salon_add_phone = Column(String(20))
    salon_instagram = Column(String(100))
    salon_rating = Column(DECIMAL(3,2), default=0)
    comments = Column(JSONB, default=list)
    salon_payment = Column(JSONB)
    salon_description = Column(Text)
    salon_types = Column(JSONB, default=list)
    private_salon = Column(Boolean, default=False)
    work_schedule = Column(JSONB, default=list)
    salon_title = Column(String(200))
    salon_additionals = Column(JSONB, default=list)
    sale_percent = Column(Integer, default=0)
    sale_limit = Column(Integer, default=0)
    location = Column(JSONB)
    salon_orient = Column(JSONB)
    salon_photos = Column(JSONB, default=list)
    salon_comfort = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    employees = relationship("Employee", back_populates="salon", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="salon", cascade="all, delete-orphan")
    services = relationship("Service", back_populates="salon", cascade="all, delete-orphan")
    salon_top_histories = relationship("SalonTopHistory", back_populates="salon", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="salon")