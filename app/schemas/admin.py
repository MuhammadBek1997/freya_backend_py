"""
Admin schemas
"""
from typing import Optional, List, Union
from datetime import datetime
from pydantic import BaseModel


class SalonTopRequest(BaseModel):
    """Salon top qilish request schema"""
    salonId: str
    isTop: bool
    duration: int = 7


class SalonTopResponse(BaseModel):
    """Salon top qilish response schema"""
    success: bool
    message: Optional[Union[str, None]] = None
    data: Optional[dict] = None


class SalonListResponse(BaseModel):
    """Salon list response schema"""
    id: str
    name: str
    address: str
    phone: str
    email: Optional[str] = None
    is_active: bool
    is_top: bool
    rating: Optional[float] = None
    created_at: str
    updated_at: str


class SalonDetailResponse(BaseModel):
    """Salon detail response schema"""
    id: str
    name: str
    address: str
    phone: str
    email: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    is_top: bool
    rating: Optional[float] = None
    photos: List[str] = []
    services: List[dict] = []
    employees: List[dict] = []
    created_at: str
    updated_at: str


class SalonTopHistoryResponse(BaseModel):
    """Salon top history response schema"""
    id: str
    salon_id: str
    admin_id: str
    action: str
    start_date: str
    end_date: Optional[str] = None
    is_active: bool
    created_at: str


class SendSMSRequest(BaseModel):
    """SMS yuborish request schema"""
    phone: str
    message: Optional[Union[str, None]] = None


class VerifySMSRequest(BaseModel):
    """SMS tasdiqlash request schema"""
    phone: str
    code: str


class SMSResponse(BaseModel):
    """SMS response schema"""
    success: bool
    message: Optional[Union[str, None]] = None
    data: Optional[dict] = None


class SalonUpdateRequest(BaseModel):
    """Salon yangilash request schema"""
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SalonPhotoUploadResponse(BaseModel):
    """Salon rasm yuklash response schema"""
    success: bool
    message: Optional[Union[str, None]] = None
    photo_url: Optional[str] = None