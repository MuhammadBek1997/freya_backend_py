from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel

class Message(BaseModel):
    __tablename__ = "messages"
    
    sender_id = Column(UUID(as_uuid=True), nullable=False)
    sender_type = Column(String(20), nullable=False)  # 'user', 'employee', 'admin'
    receiver_id = Column(UUID(as_uuid=True), nullable=False)
    receiver_type = Column(String(20), nullable=False)  # 'user', 'employee', 'admin'
    message_text = Column(Text, nullable=False)
    message_type = Column(String(20), default='text')  # 'text', 'image', 'file'
    file_url = Column(String(255))
    is_read = Column(Boolean, default=False)