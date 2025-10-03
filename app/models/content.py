from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Content(BaseModel):
    __tablename__ = "content"
    
    title = Column(String(200), nullable=False)
    description = Column(Text)
    content_type = Column(String(50), nullable=False)  # 'article', 'video', 'image', etc.
    content_data = Column(JSON)  # Flexible content storage
    image_url = Column(String(255))
    video_url = Column(String(255))
    status = Column(String(20), default='draft')  # 'draft', 'published', 'archived'
    tags = Column(JSON)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    created_by = Column(String(36), ForeignKey("admins.id"))
    
    # Relationships
    creator = relationship("Admin")
    favorites = relationship("UserFavorite", back_populates="content", cascade="all, delete-orphan")