from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class Message(BaseModel):
    __tablename__ = "messages"
    
    user_chat_id = Column(UUID(as_uuid=True), ForeignKey("user_chats.id"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), nullable=False)
    sender_type = Column(String(20), nullable=False)  # 'user', 'employee', 'admin'
    receiver_id = Column(UUID(as_uuid=True), nullable=False)
    receiver_type = Column(String(20), nullable=False)  # 'user', 'employee', 'admin'
    message_text = Column(Text, nullable=False)
    message_type = Column(String(20), default='text')  # 'text', 'image', 'file'
    file_url = Column(String(255), nullable=True)
    is_read = Column(Boolean, default=False)
    
    # Relationships
    user_chat = relationship("UserChat", back_populates="messages")