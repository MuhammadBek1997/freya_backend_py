from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from decimal import Decimal

# Salon Types Schema
class SalonType(BaseModel):
    type: str
    selected: bool = False

# Location Schema
class Location(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None  # For backward compatibility

# Salon Comfort Schema
class SalonComfort(BaseModel):
    name: str
    isActive: bool = False

# Working Hours Schema
class WorkingHours(BaseModel):
    monday: Optional[Dict[str, Any]] = None
    tuesday: Optional[Dict[str, Any]] = None
    wednesday: Optional[Dict[str, Any]] = None
    thursday: Optional[Dict[str, Any]] = None
    friday: Optional[Dict[str, Any]] = None
    saturday: Optional[Dict[str, Any]] = None
    sunday: Optional[Dict[str, Any]] = None

# Salon Create Schema
class SalonCreate(BaseModel):
    salon_name: str
    salon_phone: Optional[str] = None
    salon_instagram: Optional[str] = None
    salon_rating: Optional[Decimal] = 0
    salon_description: Optional[str] = None
    salon_types: Optional[List[SalonType]] = None
    private_salon: Optional[bool] = False
    location: Optional[Location] = None
    salon_comfort: Optional[List[SalonComfort]] = None
    salon_sale: Optional[Dict[str, Any]] = None
    is_private: Optional[bool] = False
    description_uz: Optional[str] = None
    description_ru: Optional[str] = None
    description_en: Optional[str] = None
    address_uz: Optional[str] = None
    address_ru: Optional[str] = None
    address_en: Optional[str] = None
    orientation_uz: Optional[str] = None
    orientation_ru: Optional[str] = None
    orientation_en: Optional[str] = None
    
    # Legacy fields for backward compatibility
    logo: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    working_hours: Optional[WorkingHours] = None
    photos: Optional[List[str]] = None  # Base64 formatdagi rasmlar massivi

    @validator('salon_name', pre=True)
    def validate_salon_name(cls, v, values):
        # Use salon_name if provided, otherwise fallback to name
        if not v and 'name' in values:
            return values['name']
        if not v or (isinstance(v, str) and v.strip() == ''):
            raise ValueError('Salon nomi (salon_name) majburiy')
        return v

# Salon Update Schema
class SalonUpdate(BaseModel):
    salon_name: Optional[str] = None
    salon_phone: Optional[str] = None
    salon_instagram: Optional[str] = None
    salon_rating: Optional[Decimal] = None
    salon_description: Optional[str] = None
    salon_types: Optional[List[SalonType]] = None
    private_salon: Optional[bool] = None
    location: Optional[Location] = None
    salon_comfort: Optional[List[SalonComfort]] = None
    salon_sale: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_private: Optional[bool] = None
    description_uz: Optional[str] = None
    description_ru: Optional[str] = None
    description_en: Optional[str] = None
    address_uz: Optional[str] = None
    address_ru: Optional[str] = None
    address_en: Optional[str] = None
    orientation_uz: Optional[str] = None
    orientation_ru: Optional[str] = None
    orientation_en: Optional[str] = None
    photos: Optional[List[str]] = None  # Base64 formatdagi rasmlar massivi
    logo: Optional[str] = None  # Base64 formatdagi logo rasmi


# Salon Response Schema
class SalonResponse(BaseModel):
    id: str
    salon_name: str
    salon_phone: Optional[str] = None
    salon_instagram: Optional[str] = None
    salon_rating: Optional[Decimal] = None
    salon_description: Optional[str] = None
    salon_types: Optional[List[Dict[str, Any]]] = None
    private_salon: Optional[bool] = None
    location: Optional[Dict[str, Any]] = None
    salon_comfort: Optional[List[Dict[str, Any]]] = None
    salon_sale: Optional[Dict[str, Any]] = None
    is_active: bool
    is_private: Optional[bool] = None
    description_uz: Optional[str] = None
    description_ru: Optional[str] = None
    description_en: Optional[str] = None
    address_uz: Optional[str] = None
    address_ru: Optional[str] = None
    address_en: Optional[str] = None
    orientation_uz: Optional[str] = None
    orientation_ru: Optional[str] = None
    orientation_en: Optional[str] = None

    photos: Optional[List[str]] = None  # Rasm URL manzillari
    logo: Optional[str] = None  # Logo URL manzili
    created_at: datetime
    updated_at: datetime

    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        if hasattr(v, '__str__'):
            return str(v)
        return v

    class Config:
        from_attributes = True

# Salon List Response Schema
class SalonListResponse(BaseModel):
    salons: List[SalonResponse]
    total: int
    page: int
    limit: int
    total_pages: int

# Salon Comment Create Schema
class SalonCommentCreate(BaseModel):
    text: str
    rating: int

    @validator('rating')
    def validate_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('Rating 1 dan 5 gacha bo\'lishi kerak')
        return v

# Salon Comment Response Schema
class SalonCommentResponse(BaseModel):
    id: str
    salon_id: str
    user_id: str
    text: str
    rating: int
    created_at: datetime

    class Config:
        from_attributes = True

# Nearby Salons Request Schema
class NearbySalonsRequest(BaseModel):
    latitude: float
    longitude: float
    radius: Optional[float] = 10.0
    page: Optional[int] = 1
    limit: Optional[int] = 10
    is_private: Optional[str] = ''

    @validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude -90 dan 90 gacha bo\'lishi kerak')
        return v

    @validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude -180 dan 180 gacha bo\'lishi kerak')
        return v

# Salon Types Filter Request Schema
class SalonTypesFilterRequest(BaseModel):
    salon_types: List[str]
    page: Optional[int] = 1
    limit: Optional[int] = 10
    search: Optional[str] = ''

# Photo Upload Schema
class PhotoUploadRequest(BaseModel):
    photos: List[str]  # Base64 formatdagi rasmlar massivi

    @validator('photos')
    def validate_photos(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Rasmlar majburiy va massiv formatida bo\'lishi kerak')
        return v

# Photo Delete Schema
class PhotoDeleteRequest(BaseModel):
    photo_index: int

    @validator('photo_index')
    def validate_photo_index(cls, v):
        if v < 0:
            raise ValueError('Rasm indeksi 0 dan katta bo\'lishi kerak')
        return v

# Standard Response Schemas
class StandardResponse(BaseModel):
    success: bool
    message: Optional[Union[str, None]] = None
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: Optional[Union[str, None]] = None
    error: Optional[str] = None