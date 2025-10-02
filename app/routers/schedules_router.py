from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.database import get_db
from app.models import Schedule, Salon

router = APIRouter(prefix="/schedules", tags=["schedules"])


# Pydantic схемы
class ScheduleCreate(BaseModel):
    salon_id: str
    name: str
    title: Optional[str] = None
    date: date
    repeat: bool = False
    repeat_value: Optional[str] = None
    employee_list: List[int] = []
    price: float
    full_pay: Optional[float] = None
    deposit: Optional[float] = None
    is_active: bool = True


class ScheduleUpdate(BaseModel):
    salon_id: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    date: Optional[datetime] = None
    repeat: Optional[bool] = None
    repeat_value: Optional[str] = None
    employee_list: Optional[List[int]] = None
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
    repeat: bool
    repeat_value: Optional[str]
    employee_list: Optional[List[int]]
    price: float
    full_pay: Optional[float]
    deposit: Optional[float]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# Получить все расписания с пагинацией и поиском
@router.get("/")
async def get_all_schedules(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Получить список всех расписаний с пагинацией и поиском"""
    
    offset = (page - 1) * limit
    
    # Базовый запрос
    query = db.query(Schedule)
    count_query = db.query(func.count(Schedule.id))
    
    # Поиск по имени и заголовку
    if search:
        search_filter = or_(
            Schedule.name.ilike(f"%{search}%"),
            Schedule.title.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
        count_query = count_query.filter(search_filter)
    
    # Получаем данные
    total = count_query.scalar()
    schedules = query.order_by(Schedule.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": "Jadvallar muvaffaqiyatli olindi",
        "data": schedules,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


# Получить расписание по ID
@router.get("/{id}")
async def get_schedule_by_id(
    id: str,
    db: Session = Depends(get_db)
):
    """Получить информацию о конкретном расписании"""
    
    schedule = db.query(Schedule).filter(Schedule.id == id).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jadval topilmadi"
        )
    
    return {
        "success": True,
        "message": "Jadval ma'lumotlari muvaffaqiyatli olindi",
        "data": schedule
    }


# Создать новое расписание
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новое расписание"""
    
    # Проверка существования салона
    salon = db.query(Salon).filter(Salon.id == schedule_data.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon topilmadi"
        )
    
    # Создание расписания
    new_schedule = Schedule(
        salon_id=schedule_data.salon_id,
        name=schedule_data.name,
        title=schedule_data.title,
        date=schedule_data.date,
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
        "message": "Jadval muvaffaqiyatli yaratildi",
        "data": new_schedule
    }


# Обновить расписание
@router.put("/{id}")
async def update_schedule(
    id: str,
    update_data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить расписание"""
    
    schedule = db.query(Schedule).filter(Schedule.id == id).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jadval topilmadi"
        )
    
    # Обновляем только переданные поля
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for key, value in update_dict.items():
        setattr(schedule, key, value)
    
    db.commit()
    db.refresh(schedule)
    
    return {
        "success": True,
        "message": "Jadval muvaffaqiyatli yangilandi",
        "data": schedule
    }


# Удалить расписание
@router.delete("/{id}")
async def delete_schedule(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить расписание"""
    
    schedule = db.query(Schedule).filter(Schedule.id == id).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jadval topilmadi"
        )
    
    # Сохраняем данные перед удалением
    schedule_data = {
        "id": schedule.id,
        "name": schedule.name,
        "salon_id": schedule.salon_id
    }
    
    db.delete(schedule)
    db.commit()
    
    return {
        "success": True,
        "message": "Jadval muvaffaqiyatli o'chirildi",
        "data": schedule_data
    }


# Получить расписания, сгруппированные по дням недели
@router.get("/grouped/by-date")
async def get_schedules_grouped_by_date(
    db: Session = Depends(get_db)
):
    """Получить расписания, сгруппированные по дням недели"""
    
    # Получаем все расписания, отсортированные по дате
    schedules = db.query(Schedule).order_by(Schedule.date, Schedule.created_at).all()
    
    # Группируем по дням недели
    weekdays = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
    grouped_by_date: Dict[str, List[Dict[str, Any]]] = {}
    
    for schedule in schedules:
        # Определяем день недели
        day_of_week = weekdays[schedule.date.weekday() + 1 if schedule.date.weekday() < 6 else 0]
        
        # Формируем объект расписания с дополнительными полями
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
            "start_time": "09:00",  # Значение по умолчанию
            "end_time": "18:00",    # Значение по умолчанию
            "created_at": str(schedule.created_at) if schedule.created_at else None,
            "updated_at": str(schedule.updated_at) if schedule.updated_at else None
        }
        
        # Добавляем в группу
        if day_of_week not in grouped_by_date:
            grouped_by_date[day_of_week] = []
        grouped_by_date[day_of_week].append(schedule_item)
    
    # Упорядочиваем дни недели
    ordered_weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_list_items = [
        grouped_by_date[day]
        for day in ordered_weekdays
        if day in grouped_by_date and len(grouped_by_date[day]) > 0
    ]
    
    return {
        "success": True,
        "message": "Sana bo'yicha guruhlangan jadvallar muvaffaqiyatli olindi",
        "data": day_list_items
    }


# Дополнительный эндпоинт: получить расписания по салону
@router.get("/salon/{salon_id}")
async def get_schedules_by_salon(
    salon_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    date_filter: Optional[date] = Query(None, alias="date"),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Получить расписания конкретного салона"""
    
    # Проверка существования салона
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon topilmadi"
        )
    
    offset = (page - 1) * limit
    
    # Базовый запрос
    query = db.query(Schedule).filter(Schedule.salon_id == salon_id)
    count_query = db.query(func.count(Schedule.id)).filter(Schedule.salon_id == salon_id)
    
    # Фильтры
    if date_filter:
        query = query.filter(Schedule.date == date_filter)
        count_query = count_query.filter(Schedule.date == date_filter)
    
    if is_active is not None:
        query = query.filter(Schedule.is_active == is_active)
        count_query = count_query.filter(Schedule.is_active == is_active)
    
    # Получаем данные
    total = count_query.scalar()
    schedules = query.order_by(Schedule.date.desc(), Schedule.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "message": "Salon jadvallari muvaffaqiyatli olindi",
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