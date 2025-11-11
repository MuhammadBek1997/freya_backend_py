from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class SalonBotRegistration(BaseModel):
    __tablename__ = "salon_bot_registrations"

    phone = Column(String(20), nullable=False)
    telegram_id = Column(String(50), nullable=True)
    stir = Column(String(50), nullable=True)
    salon_id = Column(String(36), ForeignKey("salons.id"), nullable=True)
    status = Column(Integer, nullable=False, default=1)  # 0 = fail, 1 = success

    # Relationships
    salon = relationship("Salon")