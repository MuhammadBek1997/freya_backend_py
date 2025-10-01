from sqlalchemy import Column, String, Boolean, Text, Integer, DECIMAL, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class Employee(BaseModel):
    __tablename__ = "employees"
    
    salon_id = Column(UUID(as_uuid=True), ForeignKey("salons.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    surname = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(100), unique=True)
    profession = Column(String(100))
    username = Column(String(50), unique=True)
    password = Column(String(255))
    avatar_url = Column(String(255))
    bio = Column(Text)
    experience_years = Column(Integer, default=0)
    rating = Column(DECIMAL(3,2), default=0)
    is_active = Column(Boolean, default=True)
    is_waiting = Column(Boolean, default=True)
    deleted_at = Column(DateTime)
    
    # Relationships
    salon = relationship("Salon", back_populates="employees")
    comments = relationship("EmployeeComment", back_populates="employee", cascade="all, delete-orphan")
    posts = relationship("EmployeePost", back_populates="employee", cascade="all, delete-orphan")