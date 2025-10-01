from sqlalchemy import Column, String, Boolean, Date, Integer, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from .base import BaseModel

class Schedule(BaseModel):
    __tablename__ = "schedules"
    
    salon_id = Column(UUID(as_uuid=True), ForeignKey("salons.id", ondelete="CASCADE"))
    name = Column(String(200), nullable=False)
    title = Column(String(300))
    date = Column(Date, nullable=False)
    repeat = Column(Boolean, default=False)
    repeat_value = Column(Integer)
    employee_list = Column(ARRAY(UUID), default=list)
    price = Column(DECIMAL(10,2), nullable=False)
    full_pay = Column(DECIMAL(10,2))
    deposit = Column(DECIMAL(10,2))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    salon = relationship("Salon", back_populates="schedules")