from sqlalchemy import Column, String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Notification(BaseModel):
    __tablename__ = "notifications"
    
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default='info')  # 'info', 'warning', 'success', 'error'
    is_read = Column(Boolean, default=False)
    data = Column(JSON)  # Additional notification data
    
    # Relationships
    user = relationship("User")