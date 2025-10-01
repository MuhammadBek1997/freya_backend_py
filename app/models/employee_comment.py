from sqlalchemy import Column, Text, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class EmployeeComment(BaseModel):
    __tablename__ = "employee_comments"
    
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    text = Column(Text, nullable=False)
    rating = Column(Integer, CheckConstraint('rating >= 1 AND rating <= 5'))
    
    # Relationships
    employee = relationship("Employee", back_populates="comments")
    user = relationship("User")