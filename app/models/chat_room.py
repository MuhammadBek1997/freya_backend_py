from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from .base import BaseModel

class ChatRoom(BaseModel):
    __tablename__ = "chat_rooms"
    
    room_name = Column(String(100))
    room_type = Column(String(20), default='private')  # 'private', 'group'
    created_by = Column(String(36), nullable=False)
    
    # Relationships
    participants = relationship("ChatParticipant", back_populates="room", cascade="all, delete-orphan")