from datetime import datetime, date, time
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel, ConfigDict

from app.database import get_db
from app.auth.dependencies import get_current_user_only
from app.models import Appointment, User, Employee, Salon, Service, Schedule
from app.schemas.salon import MobileSalonItem
from app.routers.salon_mobile import build_mobile_item, get_localized_field

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


# Yangi format uchun schema
class HistoryItem(BaseModel):
    id: str
    application_number: str
    salon: MobileSalonItem
    address: Optional[str] = None
    service_types: List[str] = []
    date: str
    time: str
    price: int
    rate: float


class HistoryAppointmentsResponse(BaseModel):
    success: bool = True
    count: int
    data: List[HistoryItem]
    pagination: PaginationMeta


# User token orqali bog‘langan bronlar: user_id yoki phone bo‘yicha
def _user_filter(current_user: User):
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


# Yordamchi: appointmentdan tarix item qurish
def _build_history_item(a: Appointment, db: Session, language: Optional[str], user_id: Optional[str]) -> HistoryItem:
    # Employee va salonni aniqlash
    emp = None
    try:
        if a.employee_id:
            emp = db.query(Employee).filter(Employee.id == a.employee_id).first()
    except Exception:
        emp = None

    salon = None
    try:
        if emp and emp.salon_id:
            salon = db.query(Salon).filter(Salon.id == emp.salon_id).first()
    except Exception:
        salon = None

    # Salon qisqa ma'lumot
    salon_item: MobileSalonItem
    if salon:
        salon_item = build_mobile_item(salon, language, db, user_id)
    else:
        # Minimal fallback
        salon_item = MobileSalonItem(
            id="",
            name="",
            description=None,
            logo=None,
            salonImage=None,
            city=None,
            rate=0.0,
            reviews=0,
            news=[],
            isFavorite=False,
        )

    # Address
    address = None
    try:
        if salon:
            address = get_localized_field(salon, "address", language)
    except Exception:
        address = None

    # Service types: salon xizmatlari nomlari (faollardan bir necha)
    service_types: List[str] = []
    try:
        if salon:
            svc_list = (
                db.query(Service)
                .filter(Service.salon_id == str(salon.id), Service.is_active == True)
                .order_by(Service.name.asc())
                .limit(5)
                .all()
            )
            service_types = [s.name for s in svc_list if s and s.name]
    except Exception:
        service_types = []
    if not service_types and a.service_name:
        service_types = [a.service_name]

    # Vaqt: start - end (service.duration yoki schedule.end_time asosida)
    start_time_str = a.application_time.strftime("%H:%M") if a.application_time else ""
    end_time_str = None
    try:
        matched_service = None
        if salon and a.service_name:
            matched_service = (
                db.query(Service)
                .filter(
                    Service.salon_id == str(salon.id),
                    func.lower(Service.name) == func.lower(a.service_name),
                )
                .first()
            )
        if matched_service and a.application_time and matched_service.duration:
            from datetime import datetime as _dt, timedelta as _td
            dt = _dt.combine(date.today(), a.application_time)
            dt_end = dt + _td(minutes=int(matched_service.duration))
            end_time_str = dt_end.strftime("%H:%M")
        else:
            # Schedule bo'yicha topishga urinamiz
            if salon and a.application_date and a.service_name:
                sched = (
                    db.query(Schedule)
                    .filter(
                        Schedule.salon_id == str(salon.id),
                        Schedule.date == a.application_date,
                        Schedule.name == a.service_name,
                    )
                    .order_by(Schedule.start_time.asc())
                    .first()
                )
                if sched and sched.end_time:
                    end_time_str = sched.end_time.strftime("%H:%M")
    except Exception:
        end_time_str = None

    time_str = start_time_str if not end_time_str else f"{start_time_str} - {end_time_str}"

    # Narx
    try:
        price_val = int(float(a.service_price)) if a.service_price is not None else 0
    except Exception:
        price_val = 0

    # Rate: employee bo'lsa undan, bo'lmasa salon rating
    rate_val = 0.0
    try:
        if emp and emp.rating is not None:
            rate_val = float(emp.rating)
        elif salon and salon.salon_rating is not None:
            rate_val = float(salon.salon_rating)
    except Exception:
        rate_val = 0.0

    return HistoryItem(
        id=str(a.id),
        application_number=a.application_number,
        salon=salon_item,
        address=address,
        service_types=service_types,
        date=(a.application_date.isoformat() if a.application_date else None),
        time=time_str,
        price=price_val,
        rate=rate_val,
    )


@router.get("/my/upcoming", response_model=HistoryAppointmentsResponse)
def my_upcoming(
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, le=100),
    page: int = Query(default=1, ge=1),
    language: Optional[str] = Header(None, alias="X-User-language"),
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
    data = [_build_history_item(i, db, language, str(current_user.id)) for i in items]
    return HistoryAppointmentsResponse(
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


@router.get("/my/expired", response_model=HistoryAppointmentsResponse)
def my_expired(
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, le=100),
    page: int = Query(default=1, ge=1),
    language: Optional[str] = Header(None, alias="X-User-language"),
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
    data = [_build_history_item(i, db, language, str(current_user.id)) for i in items]
    return HistoryAppointmentsResponse(
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


@router.get("/my/search/expired", response_model=HistoryAppointmentsResponse)
def my_search_expired(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, le=100),
    page: int = Query(default=1, ge=1),
    language: Optional[str] = Header(None, alias="X-User-language"),
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
    data = [_build_history_item(i, db, language, str(current_user.id)) for i in items]
    return HistoryAppointmentsResponse(
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


@router.get("/my/search/upcoming", response_model=HistoryAppointmentsResponse)
def my_search_upcoming(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, le=100),
    page: int = Query(default=1, ge=1),
    language: Optional[str] = Header(None, alias="X-User-language"),
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
    data = [_build_history_item(i, db, language, str(current_user.id)) for i in items]
    return HistoryAppointmentsResponse(
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