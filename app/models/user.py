from sqlalchemy import TIMESTAMP, Column, String, Boolean, DateTime, Integer, Numeric, Text, func
from sqlalchemy.orm import relationship
from .base import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(String(255), nullable=True)
    full_name = Column(String(100), nullable=True)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    username = Column(String(50), nullable=True)
    registration_step = Column(Integer, default=1)
    verification_code = Column(String(10), nullable=True)
    verification_expires_at = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    phone_verified = Column(Boolean, default=False)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    location_permission = Column(Boolean, default=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    city_id = Column(Integer, nullable=True)
    country = Column(String(100), nullable=True)
    location_updated_at = Column(
        TIMESTAMP(timezone=False), server_default=func.now()
    )
    auto_pay_for_premium = Column(Boolean, default=False)
    card_for_auto_pay = Column(String(255), nullable=True)

    # Relationships
    payment_cards = relationship("PaymentCard", back_populates="user")
    user_chats = relationship("UserChat", back_populates="user")
    employee_comments = relationship("EmployeeComment", back_populates="user")
    appointments = relationship("Appointment", back_populates="user")
    favourite_salons = relationship("UserFavouriteSalon", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    salon_ratings = relationship("SalonRatings", back_populates="user")