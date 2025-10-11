from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class Notif(BaseModel):
    __tablename__ = "notifs"
    
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    user = relationship("User")
