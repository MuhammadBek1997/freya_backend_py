from sqlalchemy import Column, DateTime, func, String
from app.database import Base
import uuid


class BaseModel(Base):
    __abstract__ = True
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(
        DateTime, server_default=func.now()
    )
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    class Config:
        orm_mode = True