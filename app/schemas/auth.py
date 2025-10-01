"""
Authentication schemas
"""
from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Login request schema"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response schema"""
    message: str
    token: str
    user: dict


class CreateAdminRequest(BaseModel):
    """Create admin request schema"""
    username: str
    email: EmailStr
    password: str
    full_name: str
    salon_id: Optional[str] = None
    role: str = "admin"


class AdminProfileResponse(BaseModel):
    """Admin profile response schema"""
    id: str
    username: str
    email: str
    full_name: str
    role: str
    salon_id: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    """User info schema"""
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str