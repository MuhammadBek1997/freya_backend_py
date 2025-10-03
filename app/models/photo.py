from sqlalchemy import Column, String
from .base import BaseModel


class Photo(BaseModel):
    __tablename__ = "photos"

    filename = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    uploader_id = Column(String(36), nullable=False)
    uploader_role = Column(String(50), nullable=False)