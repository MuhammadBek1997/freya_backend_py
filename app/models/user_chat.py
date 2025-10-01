from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class UserChat(BaseModel):
    __tablename__ = "user_chats"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    salon_id = Column(UUID(as_uuid=True), ForeignKey("salons.id"), nullable=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    chat_type = Column(String(50), default='user_salon')  # user_salon, user_employee
    last_message = Column(Text, nullable=True)
    last_message_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    unread_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="user_chats")
    salon = relationship("Salon", back_populates="user_chats")
    employee = relationship("Employee", back_populates="user_chats")
    messages = relationship("Message", back_populates="user_chat")