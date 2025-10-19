from datetime import datetime, date, time
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel, ConfigDict

from app.database import get_db
from app.auth.dependencies import get_current_user_only
from app.models import Appointment, User

router = APIRouter(prefix="/history", tags=["History"]) 


class StoryAppointmentItem(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
                "application_number": "APP-20241019-0001",
                "application_date": "2025-10-21",
                "application_time": "10:00:00",
                "employee_id": "employee_id",
                "service_name": "Haircut",
                "status": "pending",
                "is_confirmed": False,
                "is_completed": False,
                "is_cancelled": False,
            }
        },
    )

    id: str
    application_number: str
    application_date: date
    application_time: time
    employee_id: Optional[str] = None
    service_name: str
    status: str
    is_confirmed: bool
    is_completed: bool
    is_cancelled: bool


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class StoryAppointmentsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "count": 1,
                "data": [
                    {
                        "id": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
                        "application_number": "APP-20241019-0001",
                        "application_date": "2025-10-21",
                        "application_time": "10:00:00",
                        "employee_id": "employee_id",
                        "service_name": "Haircut",
                        "status": "pending",
                        "is_confirmed": False,
                        "is_completed": False,
                        "is_cancelled": False,
                    }
                ],
                "pagination": {
                    "page": 1,
                    "limit": 10,
                    "total": 1,
                    "pages": 1
                }
            }
        }
    )

    success: bool = True
    count: int
    data: List[StoryAppointmentItem]
    pagination: PaginationMeta


def _user_filter(current_user: User):
    """User token orqali bog‘langan bronlar: user_id yoki phone bo‘yicha."""
    return or_(
        Appointment.user_id == str(current_user.id),
        Appointment.phone_number == current_user.phone,
    )


def _expired_filter(now_dt: datetime):
    today = now_dt.date()
    now_time = now_dt.time()
    return or_(
        Appointment.application_date < today,
        and_(
            Appointment.application_date == today,
            Appointment.application_time < now_time,
        ),
    )


def _upcoming_filter(now_dt: datetime):
    today = now_dt.date()
    now_time = now_dt.time()
    return or_(
        Appointment.application_date > today,
        and_(
            Appointment.application_date == today,
            Appointment.application_time >= now_time,
        ),
    )


def _text_filter(q: str):
    ql = q.strip().lower()
    return or_(
        func.lower(Appointment.service_name).like(f"{ql}%"),
        func.lower(Appointment.service_name).like(f"%{ql}%"),
    )


@router.get("/my/upcoming", response_model=StoryAppointmentsResponse)
def my_upcoming(
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, le=100),
    page: int = Query(default=1, ge=1),
):
    """
    1-api: Foydalanuvchi bron qilgan xizmatlar, eskirmagan (hali ko‘rsatilmagan).
    - is_cancelled = False
    - is_completed = False
    - Vaqti kelmagan yoki bugungi, ammo kelajakdagi vaqt
    """
    now_dt = datetime.now()
    offset = (page - 1) * limit

    total = (
        db.query(func.count(Appointment.id))
        .filter(
            _user_filter(current_user),
            _upcoming_filter(now_dt),
            Appointment.is_cancelled == False,
            Appointment.is_completed == False,
        )
        .scalar()
    )

    items = (
        db.query(Appointment)
        .filter(
            _user_filter(current_user),
            _upcoming_filter(now_dt),
            Appointment.is_cancelled == False,
            Appointment.is_completed == False,
        )
        .order_by(Appointment.application_date.asc(), Appointment.application_time.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    data = [StoryAppointmentItem.model_validate(i) for i in items]
    return StoryAppointmentsResponse(
        success=True,
        count=len(data),
        data=data,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            pages=(total + limit - 1) // limit if limit else 1,
        ),
    )


@router.get("/my/expired", response_model=StoryAppointmentsResponse)
def my_expired(
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, le=100),
    page: int = Query(default=1, ge=1),
):
    """
    2-api: Faqat eskirgan (o‘tib ketgan) bron qilingan xizmatlar.
    - is_cancelled = False (bron bekor qilingan bo‘lsa, aktiv hisoblanmaydi)
    """
    now_dt = datetime.now()
    offset = (page - 1) * limit

    total = (
        db.query(func.count(Appointment.id))
        .filter(
            _user_filter(current_user),
            _expired_filter(now_dt),
            Appointment.is_cancelled == False,
        )
        .scalar()
    )

    items = (
        db.query(Appointment)
        .filter(
            _user_filter(current_user),
            _expired_filter(now_dt),
            Appointment.is_cancelled == False,
        )
        .order_by(Appointment.application_date.desc(), Appointment.application_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    data = [StoryAppointmentItem.model_validate(i) for i in items]
    return StoryAppointmentsResponse(
        success=True,
        count=len(data),
        data=data,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            pages=(total + limit - 1) // limit if limit else 1,
        ),
    )


@router.get("/my/search/expired", response_model=StoryAppointmentsResponse)
def my_search_expired(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, le=100),
    page: int = Query(default=1, ge=1),
):
    """
    3-api: Matn bo‘yicha (nomi shu matndan boshlanadi yoki matn mavjud) eskirgan bronlarni qaytaradi.
    """
    now_dt = datetime.now()
    offset = (page - 1) * limit

    total = (
        db.query(func.count(Appointment.id))
        .filter(
            _user_filter(current_user),
            _expired_filter(now_dt),
            Appointment.is_cancelled == False,
            _text_filter(q),
        )
        .scalar()
    )

    items = (
        db.query(Appointment)
        .filter(
            _user_filter(current_user),
            _expired_filter(now_dt),
            Appointment.is_cancelled == False,
            _text_filter(q),
        )
        .order_by(Appointment.application_date.desc(), Appointment.application_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    data = [StoryAppointmentItem.model_validate(i) for i in items]
    return StoryAppointmentsResponse(
        success=True,
        count=len(data),
        data=data,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            pages=(total + limit - 1) // limit if limit else 1,
        ),
    )


@router.get("/my/search/upcoming", response_model=StoryAppointmentsResponse)
def my_search_upcoming(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, le=100),
    page: int = Query(default=1, ge=1),
):
    """
    4-api: 3-api’dagi matn filtri bilan faqat aktiv, eskirmagan bronlarni qaytaradi.
    - is_cancelled = False
    - is_completed = False
    - vaqt kelmagan yoki bugun kelajakdagi
    """
    now_dt = datetime.now()
    offset = (page - 1) * limit

    total = (
        db.query(func.count(Appointment.id))
        .filter(
            _user_filter(current_user),
            _upcoming_filter(now_dt),
            Appointment.is_cancelled == False,
            Appointment.is_completed == False,
            _text_filter(q),
        )
        .scalar()
    )

    items = (
        db.query(Appointment)
        .filter(
            _user_filter(current_user),
            _upcoming_filter(now_dt),
            Appointment.is_cancelled == False,
            Appointment.is_completed == False,
            _text_filter(q),
        )
        .order_by(Appointment.application_date.asc(), Appointment.application_time.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    data = [StoryAppointmentItem.model_validate(i) for i in items]
    return StoryAppointmentsResponse(
        success=True,
        count=len(data),
        data=data,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            pages=(total + limit - 1) // limit if limit else 1,
        ),
    )


class UserBookingStatsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user id",
                "all_booked": 6,
                "cancel_booked": 2,
                "active_book": 4
            }
        }
    )

    user_id: str
    all_booked: int
    cancel_booked: int
    active_book: int


@router.get("/my/stats", response_model=UserBookingStatsResponse)
def my_booking_stats(
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
):
    total = db.query(Appointment).filter(_user_filter(current_user)).count()
    cancelled = (
        db.query(Appointment)
        .filter(_user_filter(current_user), Appointment.is_cancelled == True)
        .count()
    )
    active = (
        db.query(Appointment)
        .filter(
            _user_filter(current_user),
            Appointment.is_cancelled == False,
            Appointment.is_completed == False,
        )
        .count()
    )

    return UserBookingStatsResponse(
        user_id=str(current_user.id),
        all_booked=total,
        cancel_booked=cancelled,
        active_book=active,
    )