from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel

class TempRegistration(BaseModel):
    __tablename__ = "temp_registrations"
    
    phone = Column(String(20), nullable=False)
    verification_code = Column(String(10), nullable=False)
    verification_expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    registration_data = Column(String, nullable=True)  # JSON string for additional data
    
    def __repr__(self):
        return f"<TempRegistration(phone='{self.phone}', is_verified={self.is_verified})>"