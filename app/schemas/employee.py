from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Union
from app.schemas.salon import MobileSalonItem
from datetime import datetime

# Employee schemas
class EmployeeCreate(BaseModel):
    employee_name: str
    employee_phone: str
    employee_email: EmailStr
    role: str
    username: str
    profession: str
    employee_password: str
    work_start_time: Optional[str] = None  # HH:MM
    work_end_time: Optional[str] = None    # HH:MM

    @validator('work_start_time')
    def validate_work_start_time(cls, v):
        if v is None or v == '':
            return v
        v = v.strip()
        import re
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError("work_start_time noto'g'ri formatda (HH:MM)")
        return v

    @validator('work_end_time')
    def validate_work_end_time(cls, v):
        if v is None or v == '':
            return v
        v = v.strip()
        import re
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError("work_end_time noto'g'ri formatda (HH:MM)")
        return v

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    profession: Optional[str] = None
    work_start_time: Optional[str] = None  # HH:MM
    work_end_time: Optional[str] = None    # HH:MM

    @validator('work_start_time')
    def validate_update_work_start_time(cls, v):
        if v is None or v == '':
            return v
        v = v.strip()
        import re
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError("work_start_time noto'g'ri formatda (HH:MM)")
        return v

    @validator('work_end_time')
    def validate_update_work_end_time(cls, v):
        if v is None or v == '':
            return v
        v = v.strip()
        import re
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError("work_end_time noto'g'ri formatda (HH:MM)")
        return v

class EmployeeAvatarUpdate(BaseModel):
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

class EmployeeResponse(BaseModel):
    id: str
    salon_id: Optional[str] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    username: Optional[str] = None
    profession: Optional[str] = None
    bio: Optional[str] = None
    specialization: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_waiting: Optional[bool] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    work_start_time: Optional[str] = None
    work_end_time: Optional[str] = None
    
    # Multi-language fields
    name_uz: Optional[str] = None
    name_en: Optional[str] = None
    name_ru: Optional[str] = None
    surname_uz: Optional[str] = None
    surname_en: Optional[str] = None
    surname_ru: Optional[str] = None
    profession_uz: Optional[str] = None
    profession_en: Optional[str] = None
    profession_ru: Optional[str] = None
    bio_uz: Optional[str] = None
    bio_en: Optional[str] = None
    bio_ru: Optional[str] = None
    specialization_uz: Optional[str] = None
    specialization_en: Optional[str] = None
    specialization_ru: Optional[str] = None
    
    # Additional fields
    comment_count: Optional[int] = 0
    avg_rating: Optional[float] = 0.0
    # Yakunlangan ishlar soni (xodim necha mijozga xizmat ko'rsatgan)
    done_works: Optional[int] = 0
    salon_name: Optional[str] = None

    class Config:
        from_attributes = True

class EmployeeDetailResponse(EmployeeResponse):
    rating: Optional[float] = 0.0
    comments: List[dict] = []
    posts: List[dict] = []

# Employee comment schemas
class EmployeeCommentCreate(BaseModel):
    text: str
    rating: int
    
    @validator('rating')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

class EmployeeCommentResponse(BaseModel):
    id: str
    employee_id: str
    user_id: str
    text: str
    rating: int
    created_at: datetime
    full_name: Optional[str] = None
    user_avatar: Optional[str] = None

    class Config:
        from_attributes = True

# NEW: Employee comment list response
class EmployeeCommentListResponse(BaseModel):
    success: bool
    data: List[EmployeeCommentResponse]
    pagination: dict
    avg_rating: Optional[float] = 0.0

# Employee post schemas
class EmployeePostCreate(BaseModel):
    title: str
    description: str
    media: Optional[List[str]] = []

class EmployeePostResponse(BaseModel):
    id: str
    employee_id: str
    title: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    employee_name: Optional[str] = None
    employee_surname: Optional[str] = None
    employee_profession: Optional[str] = None
    salon_id: Optional[str] = None
    salon_name: Optional[str] = None
    media_files: List[str] = []

    class Config:
        from_attributes = True

# Employee waiting status schemas
class EmployeeWaitingStatusUpdate(BaseModel):
    is_waiting: bool

class BulkEmployeeWaitingStatusUpdate(BaseModel):
    employee_ids: List[str]
    is_waiting: bool

# Response schemas
class EmployeeListResponse(BaseModel):
    success: bool
    data: List[EmployeeResponse]
    pagination: dict

class EmployeeDetailResponseWrapper(BaseModel):
    success: bool
    data: EmployeeDetailResponse

class EmployeePostListResponse(BaseModel):
    success: bool
    data: List[EmployeePostResponse]
    pagination: dict

class SuccessResponse(BaseModel):
    success: bool
    message: Optional[Union[str, None]] = None
    data: Optional[dict] = None

# Mobile-specific employee item
class MobileEmployeeItem(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = None
    workType: Optional[str] = None
    rate: Optional[float] = 0.0
    reviewsCount: int = 0
    works: int = 0
    perWeek: int = 0

# Mobile-specific employee list response with pagination
class MobileEmployeeListResponse(BaseModel):
    success: bool
    data: List[MobileEmployeeItem]
    pagination: dict

# Mobile employee detailed response
class MobileEmployeeDetailResponse(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    works: int = 0
    reviews_count: int = 0
    per_week: int = 0
    salon: MobileSalonItem
