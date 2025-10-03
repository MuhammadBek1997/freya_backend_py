from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Post(BaseModel):
    __tablename__ = "posts"
    
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    media_urls = Column(JSON, default=list)  # Array of media file URLs
    likes_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Relationships
    employee = relationship("Employee", back_populates="general_posts")
    
    def __repr__(self):
        return f"<Post(title='{self.title}', employee_id='{self.employee_id}')>"