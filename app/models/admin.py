from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class Admin(BaseModel):
    __tablename__ = "admins"
    
    salon_id = Column(String(36), ForeignKey("salons.id"), nullable=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(String(50), default='admin')
    avatar_url = Column(String(255), nullable=True)

    # Relationships
    salon = relationship("Salon", back_populates="admins")