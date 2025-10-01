from sqlalchemy import Column, String, Boolean, Date, DateTime, Integer, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    password = Column(String(255), nullable=False)  # Changed from password_hash
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), unique=True, nullable=False)
    avatar_url = Column(String(255), nullable=True)
    birth_date = Column(Date, nullable=True)  # Changed from date_of_birth
    gender = Column(String(10), nullable=True)
    location = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    
    # Verification fields
    verification_code = Column(String(10), nullable=True)
    verification_code_expires = Column(DateTime, nullable=True)
    new_phone = Column(String(20), nullable=True)  # For phone change process
    
    # Relationships
    payments = relationship("Payment", back_populates="user")
    location_info = relationship("UserLocation", back_populates="user", uselist=False)
    payment_cards = relationship("UserPaymentCard", back_populates="user")
    favourite_salons = relationship("UserFavouriteSalon", back_populates="user")


class UserLocation(BaseModel):
    __tablename__ = "user_locations"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="location_info")


class UserPaymentCard(BaseModel):
    __tablename__ = "user_payment_cards"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_number_hash = Column(String(255), nullable=False)  # Hashed card number for security
    masked_card_number = Column(String(20), nullable=False)  # Masked for display (e.g., ****1234)
    card_type = Column(String(20), nullable=False)  # Visa, MasterCard, Uzcard, Humo
    card_holder_name = Column(String(100), nullable=False)
    expiry_month = Column(Integer, nullable=False)
    expiry_year = Column(Integer, nullable=False)
    is_default = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="payment_cards")


class UserFavouriteSalon(BaseModel):
    __tablename__ = "user_favourite_salons"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="favourite_salons")
    salon = relationship("Salon")