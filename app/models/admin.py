from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel

class Admin(BaseModel):
    __tablename__ = "admins"
    
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default='admin')
    is_active = Column(Boolean, default=True)