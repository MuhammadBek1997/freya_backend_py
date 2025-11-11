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
    # salon_phone: Optional[str] = None
    # salon_instagram: Optional[str] = None
    # salon_rating: Optional[Decimal] = 0
    # salon_description: Optional[str] = None
    # salon_types: Optional[List[SalonType]] = None
    private_salon: Optional[bool] = False
    # location: Optional[Location] = None
    # salon_comfort: Optional[List[SalonComfort]] = None
    # salon_sale: Optional[Dict[str, Any]] = None
    # is_private: Optional[bool] = False
    # description_uz: Optional[str] = None
    # description_ru: Optional[str] = None
    # description_en: Optional[str] = None
    # address_uz: Optional[str] = None
    # address_ru: Optional[str] = None
    # address_en: Optional[str] = None
    # orientation_uz: Optional[str] = None
    # orientation_ru: Optional[str] = None
    # orientation_en: Optional[str] = None
    
    # # Legacy fields for backward compatibility
    # logo: Optional[str] = None
    # name: Optional[str] = None
    # phone: Optional[str] = None
    # email: Optional[str] = None
    # description: Optional[str] = None
    # address: Optional[str] = None
    # orientation: Optional[str] = None
    # working_hours: Optional[WorkingHours] = None
    # photos: Optional[List[str]] = None  # Base64 formatdagi rasmlar massivi

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
    served_users_count: Optional[int] = 0
    employees_count: Optional[int] = 0
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

# Mobile-specific lightweight salon item schema
class MobileSalonItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    logo: Optional[str] = None
    salonImage: Optional[str] = None
    city: Optional[str] = None
    rate: Optional[float] = 0.0
    reviews: Optional[int] = 0
    news: List[str] = []
    isFavorite: bool = False
    # Koordinatalar: DEFAULT_LOCATION bilan aynan teng bo'lsa bo'sh qaytariladi
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        from_attributes = True


# Bot Registration Log Create Schema (alohida jadval uchun)
class BotRegistrationLogCreate(BaseModel):
    phone: str
    telegram_id: Optional[str] = None
    stir: Optional[str] = None
    salon_id: Optional[str] = None
    status: int  # 0 yoki 1

    @validator('status')
    def validate_status(cls, v):
        if v not in (0, 1):
            raise ValueError('status faqat 0 yoki 1 bo\'lishi kerak')
        return v

    @validator('salon_id', always=True)
    def validate_salon_id_for_success(cls, v, values):
        # Agar status=1 (muvaffaqiyatli) bo'lsa, salon_id bo'lishi maqsadga muvofiq
        status = values.get('status')
        if status == 1 and not v:
            # salon_id talabiy emas, lekin ogohlantirish sifatida xatolik ko'taramiz
            raise ValueError('status=1 bo\'lsa, salon_id berilishi kerak')
        return v


# Bot Registration Log Filter Schema (qidiruv uchun)
class BotRegistrationLogFilter(BaseModel):
    phone: Optional[str] = None
    telegram_id: Optional[str] = None
    stir: Optional[str] = None
    salon_id: Optional[str] = None
    status: Optional[int] = None

    @validator('status')
    def validate_status_optional(cls, v):
        if v is not None and v not in (0, 1):
            raise ValueError('status faqat 0 yoki 1 bo\'lishi mumkin')
        return v

    @validator('*', pre=True, always=True)
    def ensure_at_least_one(cls, v, values, **kwargs):
        # Bu validator har bir field uchun chaqiriladi; oxirida umumiy tekshiruvni qilamiz
        # Pydanticda umumiy tekshiruv uchun root_validator ishlatish mumkin, ammo bu versiyada soddaroq usul.
        return v

    @validator('phone', always=True)
    def root_check(cls, v, values):
        # At least one filter must be provided
        has_any = any([
            v,
            values.get('telegram_id'),
            values.get('stir'),
            values.get('salon_id'),
            values.get('status') is not None,
        ])
        if not has_any:
            raise ValueError('Kamida bitta filter (phone|telegram_id|stir|salon_id|status) berilishi kerak')
        return v

# Nearby-specific lightweight item for /mobile/salons/nearby
class NearbySalonItem(BaseModel):
    id: str
    name: str
    salonServices: List[str] = []
    address: Optional[str] = None
    rate: Optional[float] = 0.0
    reviewsCount: int = 0
    distance: Optional[float] = None
    isFavorite: bool = False
    photos: List[str] = []
    logo: str

# Mobile-specific salon list response with pagination
class MobileSalonListResponse(BaseModel):
    success: bool
    data: List[MobileSalonItem]
    pagination: dict

# Mobile-specific detailed address schema
class MobileAddressInfo(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance: Optional[float] = None

# Mobile-specific detailed salon response schema
class MobileSalonDetailResponse(BaseModel):
    id: str
    name: str
    logo: Optional[str] = None
    salon_images: List[str] = []
    description: Optional[str] = None
    address: MobileAddressInfo
    news: List[str] = []
    note: Optional[str] = None
    nearby_metro_station: Optional[str] = None
    phone: List[str] = []
    instagram_url: Optional[str] = None
    rate: Optional[float] = 0.0
    reviews_count: int = 0
    day_work_time: Optional[str] = None
    week_work_day: Optional[str] = None
    about_salon: Optional[str] = None
    employees_images: List[str] = []
    parking: bool = False
    water: bool = False
    coffee: bool = False
    pets: bool = False
    shower: bool = False
    towel: bool = False
    children_service: bool = False
    onlyWomen: bool = False
    isFavorite: bool = False
    served_users_count: Optional[int] = 0
    employees_count: Optional[int] = 0