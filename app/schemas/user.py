from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Union
from datetime import datetime
from enum import Enum


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
    like: Optional[bool] = None


class EmployeeContactRequest(BaseModel):
    employee_id: str


class PasswordChangeRequest(BaseModel):
    # old_password: str
    new_password: str

    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError("Parol kamida 6 ta belgidan iborat bo'lishi kerak")
        return v


class UserAvatarUpdate(BaseModel):
    avatar_url: str

    @validator('avatar_url')
    def validate_avatar_url(cls, v):
        if not v:
            raise ValueError('avatar_url talab qilinadi')
        v = v.strip()
        if len(v) > 500:
            raise ValueError('URL uzunligi 500 belgidan oshmasligi kerak')
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("URL noto'g'ri formatda (http yoki https)")
        return v


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
        # Ikki raqamli yil kiritsangiz (masalan, 26), 2000 + yil ko'rinishiga o'tkazamiz
        normalized_year = v if v >= 100 else (2000 + v)
        if normalized_year < current_year or normalized_year > current_year + 20:
            raise ValueError('Yil noto\'g\'ri')
        return normalized_year


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
        if v is not None:
            current_year = datetime.now().year
            normalized_year = v if v >= 100 else (2000 + v)
            if normalized_year < current_year or normalized_year > current_year + 20:
                raise ValueError('Yil noto\'g\'ri')
            return normalized_year
        return v


# Response schemas
class UserResponse(BaseModel):
    id: str
    # username: Optional[str] = None
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


class UserLocationResponse(BaseModel):
    latitude: Optional[float]
    longitude: Optional[float]
    address: Optional[str]
    location_updated_at: Optional[datetime]


class UserCityResponse(BaseModel):
    city: Optional[str]
    city_id: Optional[int]


class UserCityUpdate(BaseModel):
    city_id: int


class PaymentCardResponse(BaseModel):
    id: str
    masked_card_number: str
    card_type: str
    card_holder_name: str
    expiry_month: int
    expiry_year: int
    is_default: bool
    created_at: datetime

    @validator('id', pre=True)
    def convert_id_to_str(cls, v):
        if hasattr(v, '__str__'):
            return str(v)
        return v

    @validator('expiry_year', pre=False)
    def to_two_digit_year(cls, v):
        # Javobda yilni 2 raqamli (YY) ko'rinishda qaytaramiz
        if v is None:
            return v
        try:
            v_int = int(v)
            return v_int % 100
        except Exception:
            return v

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


# Karta tokenizatsiyasi uchun schemalar
class CardTokenRequest(BaseModel):
    card_number: str
    expiry_month: int
    expiry_year: int
    card_holder_name: str
    phone_number: Optional[str] = None
    temporary: Optional[bool] = True  # True - bir martalik, False - ko'p martalik

    @validator('card_number')
    def validate_card_number(cls, v):
        # Faqat raqamlar
        if not v.isdigit():
            raise ValueError('Karta raqami faqat raqamlardan iborat bo\'lishi kerak')
        # Uzunlik tekshiruvi (13-19 raqam)
        if len(v) < 13 or len(v) > 19:
            raise ValueError('Karta raqami 13-19 raqam orasida bo\'lishi kerak')
        return v

    @validator('expiry_month')
    def validate_month(cls, v):
        if v < 1 or v > 12:
            raise ValueError('Oy 1-12 orasida bo\'lishi kerak')
        return v

    @validator('expiry_year')
    def validate_year(cls, v):
        from datetime import datetime
        current_year = datetime.now().year
        normalized_year = v if v >= 100 else (2000 + v)
        if normalized_year < current_year or normalized_year > current_year + 20:
            raise ValueError(f'Yil {current_year}-{current_year + 20} orasida bo\'lishi kerak')
        return normalized_year


class CardTokenResponse(BaseModel):
    success: bool
    card_token: Optional[str] = None
    phone_number: Optional[str] = None
    temporary: bool
    error_code: Optional[int] = None
    error_note: Optional[str] = None


class DirectCardPaymentRequest(BaseModel):
    card_token: str
    amount: float
    payment_type: str  # employee_post, user_premium, salon_top
    duration_months: Optional[int] = None  # premium va salon_top uchun
    post_count: Optional[int] = None  # employee_post uchun
    employee_id: Optional[str] = None
    user_id: Optional[str] = None
    salon_id: Optional[str] = None

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Miqdor 0 dan katta bo\'lishi kerak')
        return v

    @validator('payment_type')
    def validate_payment_type(cls, v):
        allowed_types = ['employee_post', 'user_premium', 'salon_top']
        if v not in allowed_types:
            raise ValueError(f'To\'lov turi {allowed_types} dan biri bo\'lishi kerak')
        return v


class DirectCardPaymentResponse(BaseModel):
    success: bool
    payment_id: Optional[str] = None
    payment_status: Optional[int] = None
    transaction_id: Optional[str] = None
    error_code: Optional[int] = None
    error_note: Optional[str] = None