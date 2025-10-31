from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel

class PaymentCard(BaseModel):
    __tablename__ = "payment_cards"
    
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    card_token = Column(String(255), unique=True, nullable=False)
    card_number = Column(String(255), nullable=False)
    expiry_at = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User")
