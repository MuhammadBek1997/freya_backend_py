from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class UserFavouriteSalon(BaseModel):
    __tablename__ = "user_favourite_salons"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    salon_id = Column(UUID(as_uuid=True), ForeignKey("salons.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="favourite_salons")
    salon = relationship("Salon", back_populates="favourited_by_users")