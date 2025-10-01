from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class EmployeePost(BaseModel):
    __tablename__ = "employee_posts"
    
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    image_url = Column(String(255))
    
    # Relationships
    employee = relationship("Employee", back_populates="posts")