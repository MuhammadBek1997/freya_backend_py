from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class Notification(BaseModel):
    __tablename__ = "notifications"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default='info')  # 'info', 'warning', 'success', 'error'
    is_read = Column(Boolean, default=False)
    data = Column(JSONB)  # Additional notification data
    
    # Relationships
    user = relationship("User")