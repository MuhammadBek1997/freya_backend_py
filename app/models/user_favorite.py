from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class UserFavorite(BaseModel):
    __tablename__ = "user_favorites"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id", ondelete="CASCADE"))
    
    # Relationships
    user = relationship("User")
    content = relationship("Content", back_populates="favorites")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'content_id'),
    )