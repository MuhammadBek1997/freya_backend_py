from sqlalchemy import Column, String, Date, Time, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import BaseModel

class BusySlot(BaseModel):
    __tablename__ = "busy_slots"
    __table_args__ = (
        Index('ix_busy_slots_emp_date', 'employee_id', 'date'),
    )

    employee_id = Column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    reason = Column(Text, nullable=True)

    # Relationships
    employee = relationship("Employee")