from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional, List, Union
from datetime import date, time
from pydantic import BaseModel, Field

# Предполагаем, что у вас есть эти импорты
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.database import get_db
from app.i18nMini import get_translation
from app.models import Appointment, Schedule, User, Employee, Salon, Admin
from app.models.notification import Notification
from app.models.busy_slot import BusySlot
from app.models.schedule import ScheduleBook as ScheduleBookModel

router = APIRouter(prefix="/appointments", tags=["appointments"])


# Pydantic схемы
class AppointmentCreate(BaseModel):
    schedule_id: str
    user_name: str
    phone_number: str
    application_date: date
    application_time: time
    service_name: Optional[str] = None
    service_price: Optional[float] = None
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    application_date: Optional[date] = None
    application_time: Optional[time] = None
    service_name: Optional[str] = None
    service_price: Optional[float] = None
    notes: Optional[str] = None


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|cancelled|accepted|ignored|done)$")
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: str
    application_number: str
    user_id: Optional[str]
    user_name: str
    phone_number: str
    application_date: date
    application_time: time
    schedule_id: str
    employee_id: Optional[str]
    service_name: Optional[str]
    service_price: Optional[float]
    status: str
    notes: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class PaginationResponse(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


# Вспомогательная функция для генерации номера заявки
async def generate_application_number(db: Session) -> str:
    """Генерирует уникальный номер заявки"""
    count = db.query(func.count(Appointment.id)).scalar()
    return f"APP{str(count + 1).zfill(3)}"


# Создание новой заявки
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: Optional[Union[Admin, User, Employee]] = Depends(get_current_user_optional),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Создать новую заявку на прием"""
    
    # Проверка существования расписания
    schedule = db.query(Schedule).filter(Schedule.id == appointment_data.schedule_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    # Получаем salon_id и employee_id
    salon_id = schedule.salon_id
    employee_list = schedule.employee_list
    employee_id = employee_list[0] if employee_list and len(employee_list) > 0 else None
    
    # Проверка существования салона
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    # Генерация номера заявки
    application_number = await generate_application_number(db)
    
    # Проверка времени в рамках расписания (если в расписании заданы границы)
    if getattr(schedule, 'start_time', None) and getattr(schedule, 'end_time', None):
        if not (schedule.start_time <= appointment_data.application_time <= schedule.end_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_translation(language, "errors.400")
            )

    # Проверка занятости: существующая запись или busy slot
    if employee_id:
        conflict = (
            db.query(Appointment)
            .filter(
                and_(
                    Appointment.employee_id == employee_id,
                    Appointment.application_date == appointment_data.application_date,
                    Appointment.application_time == appointment_data.application_time,
                    Appointment.is_cancelled == False,
                    Appointment.status.in_(["pending", "accepted", "done"]),
                )
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=get_translation(language, "errors.409")
            )

        busy = (
            db.query(BusySlot)
            .filter(
                and_(
                    BusySlot.employee_id == employee_id,
                    BusySlot.date == appointment_data.application_date,
                    BusySlot.start_time <= appointment_data.application_time,
                    BusySlot.end_time > appointment_data.application_time,
                )
            )
            .first()
        )
        if busy:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=get_translation(language, "errors.409")
            )
    
    # Создание заявки
    new_appointment = Appointment(
        application_number=application_number,
        # user_id faqat oddiy foydalanuvchi bo'lsa yoziladi
        user_id=(current_user.id if isinstance(current_user, User) else None),
        user_name=appointment_data.user_name,
        phone_number=appointment_data.phone_number,
        application_date=appointment_data.application_date,
        application_time=appointment_data.application_time,
        schedule_id=appointment_data.schedule_id,
        employee_id=employee_id,
        service_name=appointment_data.service_name,
        service_price=appointment_data.service_price,
        notes=appointment_data.notes,
        status="pending"
    )
    
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    try:
        if isinstance(current_user, User):
            lang = (language or '').lower()
            if lang.startswith('uz'):
                title = "Appointment yaratildi"
                message = "Salonga appointment yaratdingiz"
            elif lang.startswith('ru'):
                title = "Запись создана"
                message = "Вы создали запись в салон"
            else:
                title = "Appointment created"
                message = "You created a salon appointment"
            notif = Notification(
                user_id=str(current_user.id),
                title=title,
                message=message,
                type="success",
                data={
                    "appointment_id": str(new_appointment.id),
                    "salon_id": str(salon_id),
                    "employee_id": str(employee_id) if employee_id else None,
                    "date": appointment_data.application_date.isoformat(),
                    "time": appointment_data.application_time.strftime("%H:%M"),
                },
            )
            db.add(notif)
            db.commit()
    except Exception:
        pass
    
    return {
        "success": True,
        "message": get_translation(language, "appointment.created"),
        "data": new_appointment
    }


# Получить все заявки с фильтрацией
@router.get("/")
async def get_all_appointments(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Получить список всех заявок с пагинацией"""
    
    offset = (page - 1) * limit
    
    # Базовый запрос
    query = db.query(Appointment).join(Employee, Appointment.employee_id == Employee.id, isouter=True)
    count_query = db.query(func.count(Appointment.id)).join(Employee, Appointment.employee_id == Employee.id, isouter=True)
    
    # Фильтр для админа (только заявки его салона)
    if current_user.role == "admin" and current_user.salon_id:
        query = query.filter(Employee.salon_id == current_user.salon_id)
        count_query = count_query.filter(Employee.salon_id == current_user.salon_id)
    
    # Фильтр по статусу
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
        count_query = count_query.filter(Appointment.status == status_filter)
    
    # Фильтр по пользователю
    if user_id:
        query = query.filter(Appointment.user_id == user_id)
        count_query = count_query.filter(Appointment.user_id == user_id)
    
    # Получаем данные
    total = count_query.scalar()
    appointments = query.order_by(Appointment.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": appointments,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


# Получить заявку по ID
@router.get("/{id}")
async def get_appointment_by_id(
    id: str,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Получить информацию о конкретной заявке"""
    
    appointment = db.query(Appointment).filter(Appointment.id == id).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": appointment
    }


# Обновить статус заявки
@router.patch("/{id}/status")
async def update_appointment_status(
    id: str,
    status_data: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Union[Admin, User, Employee] = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Обновить статус заявки (только для сотрудников)"""
    
    # Faqat xodim (employee)ga ruxsat, admin/superadmin/userga taqiqlanadi
    if getattr(current_user, "role", None) != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=get_translation(language, "errors.403")
        )

    appointment = db.query(Appointment).filter(Appointment.id == id).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    appointment.status = status_data.status
    if status_data.notes:
        appointment.notes = status_data.notes
    
    db.commit()
    db.refresh(appointment)
    
    return {
        "success": True,
        "message": get_translation(language, "appointment.updated"),
        "data": appointment
    }


# Получить заявки текущего пользователя
@router.get("/user/my-appointments")
async def get_user_appointments(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Получить заявки текущего пользователя"""
    
    offset = (page - 1) * limit
    
    query = db.query(Appointment).filter(Appointment.user_id == current_user.id)
    count_query = db.query(func.count(Appointment.id)).filter(Appointment.user_id == current_user.id)
    
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
        count_query = count_query.filter(Appointment.status == status_filter)
    
    total = count_query.scalar()
    appointments = query.order_by(Appointment.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": appointments,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


# Обновить заявку пользователя
@router.put("/{id}")
async def update_appointment(
    id: str,
    update_data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Обновить заявку (только свою)"""
    
    appointment = db.query(Appointment).filter(
        and_(Appointment.id == id, Appointment.user_id == current_user.id)
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    if appointment.status in ["done", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "errors.400")
        )
    
    # Обновляем только переданные поля
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "errors.400")
        )
    
    for key, value in update_dict.items():
        setattr(appointment, key, value)
    
    db.commit()
    db.refresh(appointment)
    
    return {
        "success": True,
        "message": get_translation(language, "appointment.updated"),
        "data": appointment
    }


# Отменить заявку
@router.post("/{id}/cancel")
async def cancel_appointment(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Отменить заявку (только свою)"""
    
    appointment = db.query(Appointment).filter(
        and_(Appointment.id == id, Appointment.user_id == current_user.id)
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    if appointment.status in ["done", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "errors.400")
        )
    
    appointment.status = "cancelled"
    db.commit()
    db.refresh(appointment)
    
    return {
        "success": True,
        "message": get_translation(language, "appointment.cancelled"),
        "data": appointment
    }


# Удалить заявку
@router.delete("/{id}")
async def delete_appointment(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Удалить заявку (только свою)"""
    
    appointment = db.query(Appointment).filter(
        and_(Appointment.id == id, Appointment.user_id == current_user.id)
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    if appointment.status in ["completed", "in_progress"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "errors.400")
        )
    
    db.delete(appointment)
    db.commit()
    
    return {
        "success": True,
        "message": get_translation(language, "appointment.deleted"),
        "data": appointment
    }


# Получить заявки салона по ID
@router.get("/salon/{salon_id}")
async def get_appointments_by_salon_id(
    salon_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    date_filter: Optional[date] = Query(None, alias="date"),
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Получить заявки конкретного салона"""
    
    # Проверка существования салона
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    offset = (page - 1) * limit
    
    # Базовый запрос с JOIN
    query = db.query(Appointment).join(Employee).filter(Employee.salon_id == salon_id)
    count_query = db.query(func.count(Appointment.id)).join(Employee).filter(Employee.salon_id == salon_id)
    
    # Применяем фильтры
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
        count_query = count_query.filter(Appointment.status == status_filter)
    
    if date_filter:
        query = query.filter(Appointment.application_date == date_filter)
        count_query = count_query.filter(Appointment.application_date == date_filter)
    
    if employee_id:
        query = query.filter(Appointment.employee_id == employee_id)
        count_query = count_query.filter(Appointment.employee_id == employee_id)
    
    # Получаем данные
    total = count_query.scalar()
    appointments = query.order_by(
        Appointment.application_date.desc(),
        Appointment.application_time.desc()
    ).offset(offset).limit(limit).all()

    bookings_query = db.query(ScheduleBookModel).filter(ScheduleBookModel.salon_id == salon_id)
    if date_filter:
        bookings_query = bookings_query.filter(ScheduleBookModel.time == date_filter)
    if employee_id:
        bookings_query = bookings_query.filter(ScheduleBookModel.employee_id == str(employee_id))
    bookings = bookings_query.order_by(ScheduleBookModel.time.desc()).all()
    
    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": appointments,
        "bookings": [
            {
                "id": str(b.id),
                "salon_id": str(b.salon_id),
                "full_name": b.full_name,
                "phone": b.phone,
                "time": b.time.isoformat() if b.time else None,
                "employee_id": str(b.employee_id) if b.employee_id else None,
                "created_at": b.created_at.isoformat() if getattr(b, "created_at", None) else None,
            }
            for b in bookings
        ],
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