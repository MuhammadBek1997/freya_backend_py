from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class SalonTopHistory(BaseModel):
    __tablename__ = "salon_top_history"
    
    salon_id = Column(UUID(as_uuid=True), ForeignKey("salons.id"), nullable=False)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    salon = relationship("Salon", back_populates="salon_top_histories")
    admin = relationship("Admin")