from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Analytics(BaseModel):
    __tablename__ = "analytics"

    event_type = Column(String(50), nullable=False)  # 'page_view', 'content_view', 'user_action', etc.
    user_id = Column(String(36), ForeignKey("users.id"))
    content_id = Column(String(36), ForeignKey("content.id"))
    event_data = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)

    # Relationships
    user = relationship("User")
    content = relationship("Content")