from sqlalchemy import TIMESTAMP, Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid


class BaseModel(Base):
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    class Config:
        orm_mode = True