from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, CheckConstraint, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class PaymentCard(BaseModel):
    __tablename__ = "payment_cards"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    card_number_encrypted = Column(String(255), nullable=False)
    card_holder_name = Column(String(100), nullable=False)
    expiry_month = Column(Integer, CheckConstraint('expiry_month >= 1 AND expiry_month <= 12'), nullable=False)
    expiry_year = Column(Integer, CheckConstraint('expiry_year >= EXTRACT(YEAR FROM CURRENT_DATE)'), nullable=False)
    card_type = Column(String(20))  # 'visa', 'mastercard', 'uzcard', etc.
    phone_number = Column(String(20), nullable=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_four_digits = Column(String(4), nullable=False)
    
    # Relationships
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'card_number_encrypted'),
    )