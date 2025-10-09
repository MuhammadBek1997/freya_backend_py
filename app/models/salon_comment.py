from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class SalonComment(BaseModel):
    __tablename__ = "salon_comments"

    salon_id = Column(String(36), ForeignKey("salons.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)

    # Relationships
    salon = relationship("Salon", back_populates="comments")
    user = relationship("User")