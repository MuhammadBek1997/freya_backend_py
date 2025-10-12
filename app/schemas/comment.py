from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class CommentCreate(BaseModel):
    # user_id: str = Field(..., description="Kommentariya yozayotgan foydalanuvchi IDsi")
    text: str = Field(..., min_length=1, description="Kommentariya matni")
    rating: int = Field(..., ge=0, le=5, description="Baholash (0-5)")


class CommentItem(BaseModel):
    id: str
    user_id: str
    user_name: Optional[str] = None
    owner_avatar_url: Optional[str] = None
    text: str
    rating: int
    created_at: datetime

    class Config:
        orm_mode = True


class CommentListResponse(BaseModel):
    success: bool = True
    data: List[CommentItem]
    pagination: dict