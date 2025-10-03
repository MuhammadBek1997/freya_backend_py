from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel


class Payment(BaseModel):
    __tablename__ = "payments"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=True)
    salon_id = Column(String(36), ForeignKey("salons.id"), nullable=True)
    amount = Column(Integer, nullable=False)
    payment_type = Column(String(50), nullable=False)  # employee_post, user_premium, salon_top
    transaction_id = Column(String(255), unique=True, nullable=False)
    click_trans_id = Column(String(255), nullable=True)
    status = Column(String(20), default="pending")  # pending, completed, failed, cancelled
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="payments")
    employee = relationship("Employee", back_populates="payments")
    salon = relationship("Salon", back_populates="payments")