from sqlalchemy import Column, ForeignKey, UniqueConstraint, String
from sqlalchemy.orm import relationship
from .base import BaseModel

class UserFavorite(BaseModel):
    __tablename__ = "user_favorites"
    
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    content_id = Column(String(36), ForeignKey("content.id", ondelete="CASCADE"))
    
    # Relationships
    user = relationship("User")
    content = relationship("Content", back_populates="favorites")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'content_id'),
    )