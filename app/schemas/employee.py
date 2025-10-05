from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Union
from datetime import datetime
from uuid import UUID

# Employee schemas
class EmployeeCreate(BaseModel):
    # salon_id endi majburiy emas; admin.salon_id avtomatik olinadi
    # salon_id: Optional[str] = None
    employee_name: str
    employee_phone: str
    employee_email: EmailStr
    role: str
    username: str
    profession: str
    employee_password: str

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    profession: Optional[str] = None

class EmployeeResponse(BaseModel):
    id: UUID
    salon_id: Optional[UUID] = None
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
    id: UUID
    employee_id: UUID
    user_id: UUID
    text: str
    rating: int
    created_at: datetime
    full_name: Optional[str] = None

    class Config:
        from_attributes = True

# Employee post schemas
class EmployeePostCreate(BaseModel):
    title: str
    description: str
    media: Optional[List[str]] = []

class EmployeePostResponse(BaseModel):
    id: UUID
    employee_id: UUID
    title: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    employee_name: Optional[str] = None
    employee_surname: Optional[str] = None
    employee_profession: Optional[str] = None
    salon_id: Optional[UUID] = None
    salon_name: Optional[str] = None
    media_files: List[str] = []

    class Config:
        from_attributes = True

# Employee waiting status schemas
class EmployeeWaitingStatusUpdate(BaseModel):
    is_waiting: bool

class BulkEmployeeWaitingStatusUpdate(BaseModel):
    employee_ids: List[UUID]
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