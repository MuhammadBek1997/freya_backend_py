from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime, time, timedelta
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.i18nMini import get_translation
from app.models.user import User
from app.database import get_db
from app.models import Schedule, Salon
from app.models.schedule import ScheduleBook as ScheduleBookModel
from app.models.busy_slot import BusySlot
from app.models.employee import Employee
from app.models.appointment import Appointment
from sqlalchemy import and_

router = APIRouter(prefix="/schedules", tags=["schedules"])


# Pydantic схемы
class ScheduleCreate(BaseModel):
    salon_id: str
    name: str
    title: Optional[str] = None
    date: date
    start_time: time
    end_time: time
    repeat: bool = False
    repeat_value: Optional[str] = None
    employee_list: List[str] = []
    price: float
    full_pay: Optional[float] = None
    deposit: Optional[float] = None
    is_active: bool = True

class ScheduleBookSchema(BaseModel):
    salon_id: str
    full_name: str
    phone: str
    time: datetime
    employee_id: Optional[str] = None
    booking_number: Optional[str] = None

class ScheduleUpdate(BaseModel):
    salon_id: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    repeat: Optional[bool] = None
    repeat_value: Optional[str] = None
    employee_list: Optional[List[str]] = None
    price: Optional[float] = None
    full_pay: Optional[float] = None
    deposit: Optional[float] = None
    is_active: Optional[bool] = None

class ScheduleResponse(BaseModel):
    id: str
    salon_id: str
    name: str
    title: Optional[str]
    date: date
    start_time: Optional[time]
    end_time: Optional[time]
    repeat: bool
    repeat_value: Optional[str]
    employee_list: Optional[List[str]]
    price: float
    full_pay: Optional[float]
    deposit: Optional[float]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ===== BOOKING ENDPOINTS (ANIQ ROUTE'LAR BIRINCHI) =====

@router.post("/book", status_code=status.HTTP_201_CREATED)
async def book_schedule(
    booking_data: ScheduleBookSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Забронировать время в расписании"""
    
    salon = db.query(Salon).filter(Salon.id == booking_data.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    dt = booking_data.time
    date_part = dt.date()
    time_part = dt.time()
    end_dt = datetime.combine(date_part, time_part) + timedelta(minutes=30)

    # If employee_id provided, prevent conflicts and create BusySlot
    if booking_data.employee_id:
        # Check employee working hours window
        emp = db.query(Employee).filter(Employee.id == booking_data.employee_id).first()
        if emp:
            try:
                if emp.work_start_time and emp.work_end_time:
                    ws = datetime.strptime(emp.work_start_time, "%H:%M").time()
                    we = datetime.strptime(emp.work_end_time, "%H:%M").time()
                    if not (ws < we and ws <= time_part and end_dt.time() <= we):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=get_translation(language, "errors.400")
                        )
            except Exception:
                # If parsing fails, treat as invalid window
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=get_translation(language, "errors.400")
                )
        # Validate employee belongs to salon
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))

        # Check appointments overlap
        apps = (
            db.query(Appointment)
            .filter(
                and_(
                    Appointment.employee_id == booking_data.employee_id,
                    Appointment.application_date == date_part,
                    Appointment.is_cancelled == False,
                    Appointment.status.in_(["pending", "accepted", "done"]),
                )
            )
            .all()
        )
        for a in apps:
            s_dt = datetime.combine(date_part, a.application_time)
            e_dt = datetime.combine(date_part, a.end_time) if getattr(a, "end_time", None) else s_dt + timedelta(minutes=(a.duration_minutes or 30))
            if (datetime.combine(date_part, time_part) < e_dt) and (end_dt > s_dt):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=get_translation(language, "errors.409"))

        # Check existing busy slots overlap
        bs_rows = (
            db.query(BusySlot)
            .filter(and_(BusySlot.employee_id == booking_data.employee_id, BusySlot.date == date_part))
            .all()
        )
        for bs in bs_rows:
            bs_s = datetime.combine(date_part, bs.start_time)
            bs_e = datetime.combine(date_part, bs.end_time)
            if (datetime.combine(date_part, time_part) < bs_e) and (end_dt > bs_s):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=get_translation(language, "errors.409"))
    booking_number = booking_data.booking_number or _generate_booking_number(db, date_part)

    new_booking = ScheduleBookModel(
        salon_id=booking_data.salon_id,
        full_name=booking_data.full_name,
        phone=booking_data.phone,
        time=date_part,
        start_time=time_part,
        end_time=end_dt.time(),
        employee_id=booking_data.employee_id,
        booking_number=booking_number
    )
    
    db.add(new_booking)
    # Create busy slot to block future bookings/appointments for this interval
    if booking_data.employee_id:
        bs = BusySlot(
            employee_id=booking_data.employee_id,
            date=date_part,
            start_time=time_part,
            end_time=end_dt.time(),
            reason="booking"
        )
        db.add(bs)
    db.commit()
    db.refresh(new_booking)
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": {
            "id": str(new_booking.id),
            "salon_id": str(new_booking.salon_id),
            "full_name": new_booking.full_name,
            "phone": new_booking.phone,
            "time": new_booking.time.isoformat(),
            "start_time": new_booking.start_time.strftime("%H:%M") if getattr(new_booking, "start_time", None) else None,
            "end_time": new_booking.end_time.strftime("%H:%M") if getattr(new_booking, "end_time", None) else None,
            "employee_id": str(new_booking.employee_id) if new_booking.employee_id else None,
            "booking_number": new_booking.booking_number,
            "created_at": new_booking.created_at.isoformat() if new_booking.created_at else None
        }
    }


@router.get("/book")
async def get_bookings(
    salon_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Получить все бронирования для конкретного салона"""
    
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    bookings = db.query(ScheduleBookModel).filter(
        ScheduleBookModel.salon_id == salon_id
    ).all()
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": [
            {
                "id": str(b.id),
                "salon_id": str(b.salon_id),
                "full_name": b.full_name,
                "phone": b.phone,
                "time": b.time.isoformat(),
                "start_time": b.start_time.strftime("%H:%M") if getattr(b, "start_time", None) else None,
                "end_time": b.end_time.strftime("%H:%M") if getattr(b, "end_time", None) else None,
                "employee_id": str(b.employee_id) if b.employee_id else None,
                "booking_number": getattr(b, "booking_number", None),
                "created_at": b.created_at.isoformat() if b.created_at else None
            }
            for b in bookings
        ]
    }


@router.get("/book/{id}")
async def get_booking_by_id(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Получить информацию о конкретном бронировании"""
    
    booking = db.query(ScheduleBookModel).filter(ScheduleBookModel.id == id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": {
            "id": str(booking.id),
            "salon_id": str(booking.salon_id),
            "full_name": booking.full_name,
            "phone": booking.phone,
            "time": booking.time.isoformat(),
            "start_time": booking.start_time.strftime("%H:%M") if getattr(booking, "start_time", None) else None,
            "end_time": booking.end_time.strftime("%H:%M") if getattr(booking, "end_time", None) else None,
            "employee_id": str(booking.employee_id) if booking.employee_id else None,
            "booking_number": getattr(booking, "booking_number", None),
            "created_at": booking.created_at.isoformat() if booking.created_at else None
        }
    }


@router.put("/book/{id}")
async def update_booking(
    id: str,
    booking_data: ScheduleBookSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Обновить бронирование"""
    
    booking = db.query(ScheduleBookModel).filter(ScheduleBookModel.id == id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    dt = booking_data.time
    date_part = dt.date()
    time_part = dt.time()
    end_dt = datetime.combine(date_part, time_part) + timedelta(minutes=30)
    booking_full_prev_date = booking.time
    booking_full_prev_start = booking.start_time
    booking_full_prev_end = booking.end_time

    # If employee_id provided, prevent conflicts (same logic as create)
    if booking_data.employee_id:
        # Check employee working hours window
        emp = db.query(Employee).filter(Employee.id == booking_data.employee_id).first()
        if emp:
            try:
                if emp.work_start_time and emp.work_end_time:
                    ws = datetime.strptime(emp.work_start_time, "%H:%M").time()
                    we = datetime.strptime(emp.work_end_time, "%H:%M").time()
                    if not (ws < we and ws <= time_part and end_dt.time() <= we):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=get_translation(language, "errors.400")
                        )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=get_translation(language, "errors.400")
                )
        apps = (
            db.query(Appointment)
            .filter(
                and_(
                    Appointment.employee_id == booking_data.employee_id,
                    Appointment.application_date == date_part,
                    Appointment.is_cancelled == False,
                    Appointment.status.in_(["pending", "accepted", "done"]),
                )
            )
            .all()
        )
        for a in apps:
            s_dt = datetime.combine(date_part, a.application_time)
            e_dt = datetime.combine(date_part, a.end_time) if getattr(a, "end_time", None) else s_dt + timedelta(minutes=(a.duration_minutes or 30))
            if (datetime.combine(date_part, time_part) < e_dt) and (end_dt > s_dt):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=get_translation(language, "errors.409"))

        bs_rows = (
            db.query(BusySlot)
            .filter(and_(BusySlot.employee_id == booking_data.employee_id, BusySlot.date == date_part))
            .all()
        )
        for bs in bs_rows:
            bs_s = datetime.combine(date_part, bs.start_time)
            bs_e = datetime.combine(date_part, bs.end_time)
            if (datetime.combine(date_part, time_part) < bs_e) and (end_dt > bs_s):
                # allow updating the same slot if it exactly matches previous
                if not (booking_full_prev_date == bs.date and booking_full_prev_start == bs.start_time and booking_full_prev_end == bs.end_time):
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=get_translation(language, "errors.409"))

    booking.full_name = booking_data.full_name
    booking.phone = booking_data.phone
    booking.time = date_part
    booking.start_time = time_part
    booking.end_time = end_dt.time()
    booking.employee_id = booking_data.employee_id
    
    # Update related busy slot: find previous and update or create new
    if booking.employee_id:
        prev_slot = db.query(BusySlot).filter(and_(
            BusySlot.employee_id == booking.employee_id,
            BusySlot.date == booking_full_prev_date,
            BusySlot.start_time == booking_full_prev_start,
            BusySlot.end_time == booking_full_prev_end,
        )).first()
        if prev_slot:
            prev_slot.date = date_part
            prev_slot.start_time = time_part
            prev_slot.end_time = end_dt.time()
            prev_slot.reason = "booking"
        else:
            bs = BusySlot(
                employee_id=booking.employee_id,
                date=date_part,
                start_time=time_part,
                end_time=end_dt.time(),
                reason="booking"
            )
            db.add(bs)

    if not getattr(booking, "booking_number", None):
        try:
            booking.booking_number = _generate_booking_number(db, date_part)
        except Exception:
            pass
    db.commit()
    db.refresh(booking)
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": {
            "id": str(booking.id),
            "salon_id": str(booking.salon_id),
            "full_name": booking.full_name,
            "phone": booking.phone,
            "time": booking.time.isoformat(),
            "start_time": booking.start_time.strftime("%H:%M") if getattr(booking, "start_time", None) else None,
            "end_time": booking.end_time.strftime("%H:%M") if getattr(booking, "end_time", None) else None,
            "employee_id": str(booking.employee_id) if booking.employee_id else None,
            "booking_number": getattr(booking, "booking_number", None),
            "created_at": booking.created_at.isoformat() if booking.created_at else None
        }
    }


@router.delete("/book/{id}")
async def delete_booking(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Удалить бронирование"""
    
    booking = db.query(ScheduleBookModel).filter(ScheduleBookModel.id == id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    # Delete related busy slot
    try:
        if booking.employee_id and booking.start_time and booking.end_time:
            bs = db.query(BusySlot).filter(and_(
                BusySlot.employee_id == booking.employee_id,
                BusySlot.date == booking.time,
                BusySlot.start_time == booking.start_time,
                BusySlot.end_time == booking.end_time,
            )).first()
            if bs:
                db.delete(bs)
    except Exception:
        pass

    db.delete(booking)
    db.commit()
    
    return {
        "success": True,
        "message": get_translation(language, "success")
    }


# ===== GROUPED/SPECIAL ENDPOINTS =====

@router.get("/grouped/by-date")
async def get_schedules_grouped_by_date(
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Получить расписания, сгруппированные по дням недели"""
    
    schedules = db.query(Schedule).order_by(Schedule.date, Schedule.created_at).all()
    
    weekdays = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
    grouped_by_date: Dict[str, List[Dict[str, Any]]] = {}
    
    for schedule in schedules:
        day_of_week = weekdays[schedule.date.weekday() + 1 if schedule.date.weekday() < 6 else 0]
        
        schedule_item = {
            "id": schedule.id,
            "salon_id": schedule.salon_id,
            "name": schedule.name,
            "title": schedule.title,
            "date": str(schedule.date),
            "repeat": schedule.repeat,
            "repeat_value": schedule.repeat_value,
            "employee_list": schedule.employee_list,
            "price": schedule.price,
            "full_pay": schedule.full_pay,
            "deposit": schedule.deposit,
            "is_active": schedule.is_active,
            "dayOfWeek": day_of_week,
            "start_time": (schedule.start_time.strftime("%H:%M") if getattr(schedule, "start_time", None) else "09:00"),
            "end_time": (schedule.end_time.strftime("%H:%M") if getattr(schedule, "end_time", None) else "18:00"),
            "created_at": str(schedule.created_at) if schedule.created_at else None,
            "updated_at": str(schedule.updated_at) if schedule.updated_at else None
        }
        
        if day_of_week not in grouped_by_date:
            grouped_by_date[day_of_week] = []
        grouped_by_date[day_of_week].append(schedule_item)
    
    ordered_weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_list_items = [
        grouped_by_date[day]
        for day in ordered_weekdays
        if day in grouped_by_date and len(grouped_by_date[day]) > 0
    ]
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": day_list_items
    }


@router.get("/salon/{salon_id}")
async def get_schedules_by_salon(
    salon_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    date_filter: Optional[date] = Query(None, alias="date"),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Получить расписания конкретного салона"""
    
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    offset = (page - 1) * limit
    
    query = db.query(Schedule).filter(Schedule.salon_id == salon_id)
    count_query = db.query(func.count(Schedule.id)).filter(Schedule.salon_id == salon_id)
    
    if date_filter:
        query = query.filter(Schedule.date == date_filter)
        count_query = count_query.filter(Schedule.date == date_filter)
    
    if is_active is not None:
        query = query.filter(Schedule.is_active == is_active)
        count_query = count_query.filter(Schedule.is_active == is_active)
    
    total = count_query.scalar()
    schedules = query.order_by(Schedule.date.desc(), Schedule.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": schedules,
        "salon": {
            "id": salon.id,
            "salon_name": salon.salon_name
        },
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


# ===== GENERAL SCHEDULE ENDPOINTS (UMUMIY ROUTE'LAR OXIRIDA) =====

@router.get("/")
async def get_all_schedules(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Получить список всех расписаний с пагинацией и поиском"""
    
    offset = (page - 1) * limit
    
    query = db.query(Schedule)
    count_query = db.query(func.count(Schedule.id))
    
    if search:
        search_filter = or_(
            Schedule.name.ilike(f"%{search}%"),
            Schedule.title.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
        count_query = count_query.filter(search_filter)
    
    total = count_query.scalar()
    schedules = query.order_by(Schedule.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": schedules,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Создать новое расписание"""
    
    salon = db.query(Salon).filter(Salon.id == schedule_data.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    if schedule_data.start_time >= schedule_data.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be earlier than end time"
        )

    new_schedule = Schedule(
        salon_id=schedule_data.salon_id,
        name=schedule_data.name,
        title=schedule_data.title,
        date=schedule_data.date,
        start_time=schedule_data.start_time,
        end_time=schedule_data.end_time,
        repeat=schedule_data.repeat,
        repeat_value=schedule_data.repeat_value,
        employee_list=schedule_data.employee_list,
        price=schedule_data.price,
        full_pay=schedule_data.full_pay,
        deposit=schedule_data.deposit,
        is_active=schedule_data.is_active
    )
    
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": new_schedule
    }


@router.get("/{id}")
async def get_schedule_by_id(
    id: str,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Получить информацию о конкретном расписании"""
    
    schedule = db.query(Schedule).filter(Schedule.id == id).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": schedule
    }


@router.put("/{id}")
async def update_schedule(
    id: str,
    update_data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Обновить расписание"""
    
    schedule = db.query(Schedule).filter(Schedule.id == id).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    if update_data.start_time is not None and update_data.end_time is not None:
        if update_data.start_time >= update_data.end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be earlier than end time"
            )

    update_dict = update_data.model_dump(exclude_unset=True)
    
    for key, value in update_dict.items():
        setattr(schedule, key, value)
    
    db.commit()
    db.refresh(schedule)
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": schedule
    }


@router.delete("/{id}")
async def delete_schedule(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Удалить расписание"""
    
    schedule = db.query(Schedule).filter(Schedule.id == id).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    schedule_data = {
        "id": schedule.id,
        "name": schedule.name,
        "salon_id": schedule.salon_id
    }
    
    db.delete(schedule)
    db.commit()
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": schedule_data
    }
def _generate_booking_number(db: Session, day: date) -> str:
    import secrets
    base = f"BOOK-{day.strftime('%Y%m%d')}"
    while True:
        suffix = secrets.token_hex(4).upper()
        number = f"{base}-{suffix}"
        exists = db.query(ScheduleBookModel).filter(ScheduleBookModel.booking_number == number).first()
        if not exists:
            return number
@router.get("/book/number/{booking_number}")
async def get_booking_by_number(
    booking_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    booking = db.query(ScheduleBookModel).filter(ScheduleBookModel.booking_number == booking_number).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": {
            "id": str(booking.id),
            "salon_id": str(booking.salon_id),
            "full_name": booking.full_name,
            "phone": booking.phone,
            "time": booking.time.isoformat(),
            "start_time": booking.start_time.strftime("%H:%M") if getattr(booking, "start_time", None) else None,
            "end_time": booking.end_time.strftime("%H:%M") if getattr(booking, "end_time", None) else None,
            "employee_id": str(booking.employee_id) if booking.employee_id else None,
            "booking_number": booking.booking_number,
        }
    }

@router.delete("/book/number/{booking_number}")
async def delete_booking_by_number(
    booking_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    booking = db.query(ScheduleBookModel).filter(ScheduleBookModel.booking_number == booking_number).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))
    try:
        if booking.employee_id and booking.start_time and booking.end_time:
            bs = db.query(BusySlot).filter(and_(
                BusySlot.employee_id == booking.employee_id,
                BusySlot.date == booking.time,
                BusySlot.start_time == booking.start_time,
                BusySlot.end_time == booking.end_time,
            )).first()
            if bs:
                db.delete(bs)
    except Exception:
        pass
    db.delete(booking)
    db.commit()
    return {"success": True, "message": get_translation(language, "success")}
