from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Union
from datetime import datetime
from enum import Enum
import uuid


class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class UserRegistrationStep1(BaseModel):
    phone: str
    password: str

    @validator('phone')
    def validate_phone(cls, v):
        if not v.startswith('+998') or len(v) != 13:
            raise ValueError('Telefon raqam +998XXXXXXXXX formatida bo\'lishi kerak')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Parol kamida 6 ta belgidan iborat bo\'lishi kerak')
        return v


class PhoneVerification(BaseModel):
    phone: str
    verification_code: str

    @validator('phone')
    def validate_phone(cls, v):
        if not v.startswith('+998') or len(v) != 13:
            raise ValueError('Telefon raqam +998XXXXXXXXX formatida bo\'lishi kerak')
        return v

    @validator('verification_code')
    def validate_code(cls, v):
        if len(v) != 6 or not v.isdigit():
            raise ValueError('Tasdiqlash kodi 6 ta raqamdan iborat bo\'lishi kerak')
        return v


class UserRegistrationStep2(BaseModel):
    phone: str
    username: str
    email: Optional[EmailStr] = None

    @validator('phone')
    def validate_phone(cls, v):
        if not v.startswith('+998') or len(v) != 13:
            raise ValueError('Telefon raqam +998XXXXXXXXX formatida bo\'lishi kerak')
        return v

    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username kamida 3 ta belgidan iborat bo\'lishi kerak')
        return v


class UserLogin(BaseModel):
    phone: str
    password: str

    @validator('phone')
    def validate_phone(cls, v):
        if not v.startswith('+998') or len(v) != 13:
            raise ValueError('Telefon raqam +998XXXXXXXXX formatida bo\'lishi kerak')
        return v


class PasswordResetRequest(BaseModel):
    phone: str

    @validator('phone')
    def validate_phone(cls, v):
        if not v.startswith('+998') or len(v) != 13:
            raise ValueError('Telefon raqam +998XXXXXXXXX formatida bo\'lishi kerak')
        return v


class PasswordReset(BaseModel):
    phone: str
    verification_code: str
    new_password: str

    @validator('phone')
    def validate_phone(cls, v):
        if not v.startswith('+998') or len(v) != 13:
            raise ValueError('Telefon raqam +998XXXXXXXXX formatida bo\'lishi kerak')
        return v

    @validator('verification_code')
    def validate_code(cls, v):
        if len(v) != 6 or not v.isdigit():
            raise ValueError('Tasdiqlash kodi 6 ta raqamdan iborat bo\'lishi kerak')
        return v

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Parol kamida 6 ta belgidan iborat bo\'lishi kerak')
        return v


class PhoneChangeRequest(BaseModel):
    phone: str

    @validator('phone')
    def validate_phone(cls, v):
        if not v.startswith('+998') or len(v) != 13:
            raise ValueError('Telefon raqam +998XXXXXXXXX formatida bo\'lishi kerak')
        return v


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    birth_date: Optional[datetime] = None
    gender: Optional[GenderEnum] = None

    @validator('username')
    def validate_username(cls, v):
        if v and len(v) < 3:
            raise ValueError('Username kamida 3 ta belgidan iborat bo\'lishi kerak')
        return v


class UserLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None

    @validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude -90 va 90 orasida bo\'lishi kerak')
        return v

    @validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude -180 va 180 orasida bo\'lishi kerak')
        return v


class FavouriteSalonRequest(BaseModel):
    salon_id: str


class PaymentCardAdd(BaseModel):
    card_number: str
    card_holder_name: str
    expiry_month: int
    expiry_year: int
    is_default: Optional[bool] = False

    @validator('card_number')
    def validate_card_number(cls, v):
        # Remove spaces and validate
        clean_number = v.replace(' ', '')
        if not clean_number.isdigit() or len(clean_number) < 13 or len(clean_number) > 19:
            raise ValueError('Karta raqami noto\'g\'ri formatda')
        return clean_number

    @validator('expiry_month')
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError('Oy 1-12 orasida bo\'lishi kerak')
        return v

    @validator('expiry_year')
    def validate_year(cls, v):
        current_year = datetime.now().year
        if v < current_year or v > current_year + 20:
            raise ValueError('Yil noto\'g\'ri')
        return v


class PaymentCardUpdate(BaseModel):
    card_holder_name: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    is_default: Optional[bool] = None

    @validator('expiry_month')
    def validate_month(cls, v):
        if v and not 1 <= v <= 12:
            raise ValueError('Oy 1-12 orasida bo\'lishi kerak')
        return v

    @validator('expiry_year')
    def validate_year(cls, v):
        if v:
            current_year = datetime.now().year
            if v < current_year or v > current_year + 20:
                raise ValueError('Yil noto\'g\'ri')
        return v


# Response schemas
class UserResponse(BaseModel):
    id: uuid.UUID
    username: Optional[str] = None
    email: Optional[str] = None
    phone: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    birth_date: Optional[datetime] = None
    gender: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str
        }


class UserLocationResponse(BaseModel):
    latitude: Optional[float]
    longitude: Optional[float]
    address: Optional[str]
    location_updated_at: Optional[datetime]


class PaymentCardResponse(BaseModel):
    id: int
    masked_card_number: str
    card_type: str
    card_holder_name: str
    expiry_month: int
    expiry_year: int
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    success: bool
    message: Optional[Union[str, None]] = None
    token: str
    user: UserResponse


class TokenResponse(BaseModel):
    success: bool
    message: Optional[Union[str, None]] = None
    token: str