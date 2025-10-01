from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from .base import BaseModel

class Analytics(BaseModel):
    __tablename__ = "analytics"
    
    event_type = Column(String(50), nullable=False)  # 'page_view', 'content_view', 'user_action', etc.
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"))
    event_data = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    
    # Relationships
    user = relationship("User")
    content = relationship("Content")