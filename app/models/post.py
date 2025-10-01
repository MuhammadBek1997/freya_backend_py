from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class Post(BaseModel):
    __tablename__ = "posts"
    
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    media_urls = Column(JSONB, default=list)  # Array of media file URLs
    likes_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Relationships
    employee = relationship("Employee", back_populates="general_posts")
    
    def __repr__(self):
        return f"<Post(title='{self.title}', employee_id='{self.employee_id}')>"