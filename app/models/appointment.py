from sqlalchemy import Column, Date, Float, String, Boolean, DateTime, Integer, ForeignKey, Text, Numeric, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class Appointment(BaseModel):
    __tablename__ = "appointments"
    
    application_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    user_name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=False)
    application_date = Column(Date, nullable=False)
    application_time = Column(Time, nullable=False)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("schedules.id"), nullable=False)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    service_name = Column(String(255), nullable=False)
    service_price = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), default='pending')
    notes = Column(Text, nullable=True)
    is_confirmed = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    is_cancelled = Column(Boolean, default=False)
    cancellation_reason = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="appointments")
    schedule = relationship("Schedule", back_populates="appointments")
    employee = relationship("Employee", back_populates="appointments")