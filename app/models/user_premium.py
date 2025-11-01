from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel


class UserPremium(BaseModel):
    __tablename__ = "user_premiums"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_date = Column(DateTime, nullable=False)
    duration_months = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", backref="premiums")