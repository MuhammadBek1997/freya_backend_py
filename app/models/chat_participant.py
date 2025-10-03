from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from .base import BaseModel

class ChatParticipant(BaseModel):
    __tablename__ = "chat_participants"
    
    room_id = Column(String(36), ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    participant_id = Column(String(36), nullable=False)
    participant_type = Column(String(20), nullable=False)  # 'user', 'employee', 'admin'
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    room = relationship("ChatRoom", back_populates="participants")