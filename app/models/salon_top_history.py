from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class SalonTopHistory(BaseModel):
    __tablename__ = "salon_top_history"
    
    salon_id = Column(String(36), ForeignKey("salons.id"), nullable=False)
    admin_id = Column(String(36), ForeignKey("admins.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    action = Column(String(255), nullable=False)  # e.g., 'promoted', 'demoted'
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    salon = relationship("Salon", back_populates="salon_top_histories")
    admin = relationship("Admin")