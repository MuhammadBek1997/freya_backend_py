from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class Appointment(BaseModel):
    __tablename__ = "appointments"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    salon_id = Column(UUID(as_uuid=True), ForeignKey("salons.id"), nullable=False)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    service_name = Column(String(255), nullable=False)
    service_price = Column(Numeric(10, 2), nullable=False)
    appointment_date = Column(DateTime, nullable=False)
    appointment_time = Column(String(10), nullable=False)
    status = Column(String(50), default='pending')
    notes = Column(Text, nullable=True)
    is_confirmed = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    is_cancelled = Column(Boolean, default=False)
    cancellation_reason = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="appointments")
    salon = relationship("Salon", back_populates="appointments")
    employee = relationship("Employee", back_populates="appointments")