from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import BaseModel

class EmployeeTranslation(BaseModel):
    __tablename__ = "employee_translations"
    
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False)
    language_code = Column(String(10), nullable=False)  # e.g., 'uz', 'ru', 'en'
    name = Column(String(100), nullable=True)
    surname = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    specialization = Column(String(255), nullable=True)
    position = Column(String(100), nullable=True)
    profession = Column(String(100), nullable=True)
    
    # Relationships
    employee = relationship("Employee", back_populates="translations")
    
    def __repr__(self):
        return f"<EmployeeTranslation(employee_id='{self.employee_id}', language='{self.language_code}')>"


class SalonTranslation(BaseModel):
    __tablename__ = "salon_translations"
    
    salon_id = Column(String(36), ForeignKey("salons.id"), nullable=False)
    language_code = Column(String(10), nullable=False)  # e.g., 'uz', 'ru', 'en'
    salon_name = Column(String(200), nullable=True)
    salon_description = Column(Text, nullable=True)
    salon_title = Column(String(200), nullable=True)
    
    # Relationships
    salon = relationship("Salon", back_populates="translations")
    
    def __repr__(self):
        return f"<SalonTranslation(salon_id='{self.salon_id}', language='{self.language_code}')>"