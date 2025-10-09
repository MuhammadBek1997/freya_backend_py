from sqlalchemy import Column, String, Boolean, Text, Integer, DECIMAL, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Salon(BaseModel):
    __tablename__ = "salons"
    
    salon_name = Column(String(200), nullable=False)
    salon_phone = Column(String(20))
    salon_instagram = Column(String(100))
    salon_rating = Column(DECIMAL(3,2), default=0)
    salon_types = Column(JSON, default=list)
    private_salon = Column(Boolean, default=False)
    location = Column(JSON)
    salon_comfort = Column(JSON, default=list)
    salon_sale = Column(JSON)
    photos = Column(JSON, default=list)
    # Salon logo URL (ixtiyoriy)
    logo = Column(String(500))
    is_active = Column(Boolean, default=True)
    is_private = Column(Boolean, default=False)
    is_top = Column(Boolean, default=False)
    description_uz = Column(Text)
    description_ru = Column(Text)
    description_en = Column(Text)
    address_uz = Column(Text)
    address_ru = Column(Text)
    address_en = Column(Text)
    orientation_uz = Column(Text)  # 0: portrait, 1: landscape
    orientation_ru = Column(Text)  # 0: portrait, 1: landscape
    orientation_en = Column(Text)  # 0: portrait, 1: landscape
    
    # Relationships
    employees = relationship("Employee", back_populates="salon", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="salon", cascade="all, delete-orphan")
    services = relationship("Service", back_populates="salon", cascade="all, delete-orphan")
    salon_top_histories = relationship("SalonTopHistory", back_populates="salon", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="salon")
    admins = relationship("Admin", back_populates="salon")
    # appointments = relationship("Appointment", back_populates="salon")
    user_chats = relationship("UserChat", back_populates="salon")
    translations = relationship("SalonTranslation", back_populates="salon", cascade="all, delete-orphan")
    favourited_by_users = relationship("UserFavouriteSalon", back_populates="salon")
    schedule_books = relationship("ScheduleBook", back_populates="salon")
    comments = relationship("SalonComment", back_populates="salon", cascade="all, delete-orphan")