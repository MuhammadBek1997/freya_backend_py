from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class UserSession(BaseModel):
    __tablename__ = "user_sessions"
    
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash = Column(String(255), nullable=False)
    device_info = Column(JSON)
    ip_address = Column(String(45))
    expires_at = Column(DateTime, nullable=False)
    
    # Relationships
    user = relationship("User")