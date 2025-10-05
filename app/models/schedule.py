from sqlalchemy import Column, String, Boolean, Date, Integer, DECIMAL, ForeignKey, Text, Time, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Schedule(BaseModel):
    __tablename__ = "schedules"
    
    salon_id = Column(String(36), ForeignKey("salons.id", ondelete="CASCADE"))
    name = Column(String(200), nullable=False)
    title = Column(String(300))
    date = Column(Date, nullable=False)
    # Ish vaqti (start/end) qo'shildi
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    repeat = Column(Boolean, default=False)
    repeat_value = Column(Text)
    employee_list = Column(JSON, default=list)
    price = Column(DECIMAL(10,2), nullable=False)
    full_pay = Column(DECIMAL(10,2))
    deposit = Column(DECIMAL(10,2))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    salon = relationship("Salon", back_populates="schedules")
    appointments = relationship("Appointment", back_populates="schedule")

class ScheduleBook(BaseModel):
    __tablename__ = "schedule_books"

    salon_id = Column(String(36), ForeignKey("salons.id", ondelete="CASCADE"))
    full_name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    time = Column(Date, nullable=False)
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=True)
    
    # Relationships
    salon = relationship("Salon", back_populates="schedule_books")
    employee = relationship("Employee", back_populates="schedule_books")