from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Union
from datetime import date, datetime, time, timedelta
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.i18nMini import get_translation
from app.models.salon import Salon
from app.models.schedule import Schedule
from app.models.employee import Employee
from app.models.appointment import Appointment
from app.models.payment_card import PaymentCard
from app.models.service import Service
from app.schemas.schedule_mobile import (
    MobileScheduleListResponse,
    MobileScheduleServiceItem,
    MobileScheduleFiltersResponse,
    MobileScheduleFilters,
)


# Appointment yaratish uchun schema'lar
class MobileAppointmentCreate(BaseModel):
    salon_id: str
    service_id: Optional[str] = None  # Service model'dan
    schedule_id: str
    employee_id: str
    application_date: date
    application_time: time
    user_name: str
    phone_number: str
    only_card: bool = False
    payment_card_id: Optional[str] = None  # only_card=True bo'lsa majburiy
    notes: Optional[str] = None

class MobileAppointmentResponse(BaseModel):
    success: bool
    message: str
    appointment_id: Optional[str] = None
    application_number: Optional[str] = None


router = APIRouter(prefix="/mobile/schedules", tags=["Mobile Schedules"])


def _weekday_short(d: date) -> str:
    names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    return names[d.weekday()]


def _build_time_slots(
    start: Optional[time], end: Optional[time], slot_minutes: int = 30
) -> List[str]:
    if not start or not end:
        return []
    dt = datetime.combine(date.today(), start)
    et = datetime.combine(date.today(), end)
    slots: List[str] = []
    while dt <= et:
        slots.append({"time": dt.strftime("%H:%M"), "empty_slot": 0})
        dt += timedelta(minutes=slot_minutes)
    return slots


@router.get(
    "/filters/{salon_id}",
    response_model=MobileScheduleFiltersResponse,
    summary="Mobil: Jadval filtrlari",
    description="X-User-language (uz|ru|en) headeri bo'yicha ko'p tilli misollar",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "uz": {
                            "summary": "Uzbek example",
                            "value": {
                                "success": True,
                                "data": {
                                    "directions": [
                                        "Umumiy massaj",
                                        "Sportiv massaj",
                                        "Manual terapiya",
                                    ],
                                    "times": ["7:00-8:00", "8:00-9:00", "9:00-10:00"],
                                    "employees": ["Anna", "Sara", "Luybov"],
                                },
                            },
                        },
                        "ru": {
                            "summary": "Russian example",
                            "value": {
                                "success": True,
                                "data": {
                                    "directions": [
                                        "Общий массаж",
                                        "Спортивный массаж",
                                        "Мануальная терапия",
                                    ],
                                    "times": ["7:00-8:00", "8:00-9:00", "9:00-10:00"],
                                    "employees": ["Анна", "Сара", "Любовь"],
                                },
                            },
                        },
                        "en": {
                            "summary": "English example",
                            "value": {
                                "success": True,
                                "data": {
                                    "directions": [
                                        "General massage",
                                        "Sports massage",
                                        "Manual therapy",
                                    ],
                                    "times": ["7:00-8:00", "8:00-9:00", "9:00-10:00"],
                                    "employees": ["Anna", "Sara", "Lyubov"],
                                },
                            },
                        },
                    }
                }
            }
        }
    },
)
async def get_mobile_schedule_filters(
    salon_id: str,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Mobil UI uchun jadval filtrlari: yo'nalishlar, vaqt oraliqlari, xodimlar"""

    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    schedules: List[Schedule] = (
        db.query(Schedule)
        .filter(Schedule.salon_id == salon_id)
        .filter(Schedule.is_active == True)
        .order_by(Schedule.date.desc())
        .all()
    )

    directions: List[str] = sorted({s.name for s in schedules if s.name})

    # Vaqt oraliqlari (soatlik segmentlar)
    start_hour = 7
    end_hour = 22
    times: List[str] = [f"{h}:00-{h+1}:00" for h in range(start_hour, end_hour)]

    # Xodimlar
    employee_ids: List[str] = []
    for s in schedules:
        if s.employee_list:
            employee_ids.extend([str(eid) for eid in s.employee_list])
    employee_ids = list(sorted(set(employee_ids)))
    employees = []
    if employee_ids:
        employees = [
            e.full_name
            for e in db.query(Employee).filter(Employee.id.in_(employee_ids)).all()
            if e.full_name
        ]

    return MobileScheduleFiltersResponse(
        success=True,
        data=MobileScheduleFilters(
            directions=directions, times=times, employees=employees
        ),
    )


@router.get(
    "/salon/{salon_id}",
    response_model=MobileScheduleListResponse,
    summary="Mobil: Salon bo'yicha jadval ro'yxati",
    description="X-User-language (uz|ru|en) headeri bo'yicha ko'p tilli misollar",
    responses={
        200: {
            "description": "Success",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [
                            {
                                "id": "1",
                                "salon_id": "1",
                                "name": "Service 1",
                                "title": "Title 1",
                                "price": 100.0,
                                "date": "2022-10-10",
                                "day": "Monday",
                                "employees": [
                                    {
                                        "id": "1",
                                        "name": "Anna",
                                        "reviewsCount": 10,
                                        "rate": 5.0,
                                        "workType": "Hairstylist",
                                        "avatar": "https://example.com/anna.jpg",
                                    }
                                ],
                                "times": [{"time": "08:00-09:00", "empty_slot": 0}],
                                "onlyCard": False,
                            }
                        ],
                        "pagination": {
                            "page": 1,
                            "limit": 10,
                            "total": 100,
                            "pages": 10,
                        },
                    }
                }
            },
        }
    },
)
async def get_mobile_schedules_by_salon(
    salon_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    date_filter: Optional[date] = Query(None, alias="date"),
    direction: Optional[str] = Query(None),
    start_hour: Optional[int] = Query(None),
    end_hour: Optional[int] = Query(None),
    employee_id: Optional[str] = Query(None),
    slot_minutes: int = Query(30, ge=10, le=120),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Mobil UI uchun salon bo'yicha jadval ro'yxati, filtrlash va vaqt slotlari bilan"""

    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    offset = (page - 1) * limit

    query = db.query(Schedule).filter(Schedule.salon_id == salon_id)
    count_query = db.query(func.count(Schedule.id)).filter(
        Schedule.salon_id == salon_id
    )

    if date_filter:
        query = query.filter(Schedule.date == date_filter)
        count_query = count_query.filter(Schedule.date == date_filter)

    if direction:
        query = query.filter(Schedule.name.ilike(f"%{direction}%"))
        count_query = count_query.filter(Schedule.name.ilike(f"%{direction}%"))

    if employee_id:
        query = query.filter(Schedule.employee_list.contains([employee_id]))
        count_query = count_query.filter(Schedule.employee_list.contains([employee_id]))

    # Time range filter by hours if provided
    if start_hour is not None and end_hour is not None:
        st = time(hour=start_hour)
        et = time(hour=end_hour)
        query = query.filter(and_(Schedule.start_time <= et, Schedule.end_time >= st))
        count_query = count_query.filter(
            and_(Schedule.start_time <= et, Schedule.end_time >= st)
        )

    total = count_query.scalar() or 0
    schedules: List[Schedule] = (
        query.order_by(Schedule.date.asc(), Schedule.start_time.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Prepare employee id -> name cache
    emp_cache: dict = {}

    def get_emp(eid: str) -> Optional[str]:
        if not eid:
            return None
        if eid in emp_cache:
            return emp_cache[eid]
        emp = db.query(Employee).filter(Employee.id == eid).first()
        return {
            "id": str(eid),
            "name": emp.name if emp and emp.name else "",
            "avatar": emp.avatar_url,  # Placeholder, replace with actual avatar URL if available
            "workType": emp.profession if emp and emp.profession else "",
            "rate": emp.rating if emp and emp.rating else 0.0,
            "reviewsCount": 0,
        }
        # name = emp.name if emp and emp.name else None
        # if name:
        #     emp_cache[eid] = name
        # return name

    items: List[MobileScheduleServiceItem] = []
    for s in schedules:
        employees: List[str] = []
        if s.employee_list:
            for eid in s.employee_list:
                employees.append(get_emp(str(eid)))
                # n = get_emp_name(str(eid))
                # if n:
                #     employees.append(n)

        slots = _build_time_slots(s.start_time, s.end_time, slot_minutes)

        items.append(
            MobileScheduleServiceItem(
                id=str(s.id),
                salon_id=str(s.salon_id),
                name=s.name,
                title=s.title,
                price=float(s.price) if s.price is not None else 0.0,
                date=str(s.date) if s.date else None,
                day=_weekday_short(s.date) if s.date else None,
                employees=employees,
                times=slots,
                onlyCard=False,
            )
        )

    return MobileScheduleListResponse(
        success=True,
        data=items,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if limit else 1,
        },
    )


# @router.get(
#     "/day/{day}/employee/{employee_id}",
#     response_model=MobileScheduleServiceItem,
#     summary="Mobil: Kun va xodim bo'yicha jadval",
#     description="X-User-language (uz|ru|en) headeri bo'yicha ko'p tilli misollar",
# )
# async def get_mobile_schedule_by_day_and_employee(
#     day: str,
#     employee_id: str,
#     db: Session = Depends(get_db),
#     language: Union[str, None] = Header(None, alias="X-User-language"),
# ):
#     """Mobil UI uchun employee va kunlik kuni ro'yxati, filtrlash va vaqt slotlari bilan"""
#     if not employee:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=get_translation(language, "errors.404"),
#         )
#     day_date = datetime.strptime(day, "%Y-%m-%d").date()
#     query = db.query(Schedule).filter(
#         and_(
#             Schedule.date == day_date,
#             Schedule.employee_list.like(f"%{employee_id}%")
#         )
#     )
#     schedule: Schedule = query.first()

#     if not schedule:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=get_translation(language, "errors.404"),
#         )

#     slots = _build_time_slots(schedule.start_time, schedule.end_time, 30)


@router.post("/appointments", response_model=MobileAppointmentResponse)
async def create_appointment(
    appointment_data: MobileAppointmentCreate,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Yangi appointment yaratish - salon, servis, vaqt, employee va karta tekshirish bilan"""
    try:
        # 1. Salon mavjudligini tekshirish
        salon = db.query(Salon).filter(
            and_(
                Salon.id == appointment_data.salon_id,
                Salon.is_active == True
            )
        ).first()
        
        if not salon:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404") or "Salon topilmadi"
            )

        # 2. Schedule mavjudligini tekshirish
        schedule = db.query(Schedule).filter(
            and_(
                Schedule.id == appointment_data.schedule_id,
                Schedule.salon_id == appointment_data.salon_id,
                Schedule.date == appointment_data.application_date,
                Schedule.is_active == True
            )
        ).first()
        
        if not schedule:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404") or "Jadval topilmadi"
            )

        # 3. Employee mavjudligini va schedule'da borligini tekshirish
        employee = db.query(Employee).filter(
            and_(
                Employee.id == appointment_data.employee_id,
                Employee.salon_id == appointment_data.salon_id,
                Employee.is_active == True
            )
        ).first()
        
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404") or "Xodim topilmadi"
            )
        
        # Employee schedule'da borligini tekshirish
        if schedule.employee_list and appointment_data.employee_id not in schedule.employee_list:
            raise HTTPException(
                status_code=400,
                detail=get_translation(language, "errors.400") or "Xodim bu jadvalda mavjud emas"
            )

        # 4. Service mavjudligini tekshirish (agar berilgan bo'lsa)
        service_name = schedule.name  # Default
        service_price = float(schedule.price)
        
        if appointment_data.service_id:
            service = db.query(Service).filter(
                and_(
                    Service.id == appointment_data.service_id,
                    Service.salon_id == appointment_data.salon_id,
                    Service.is_active == True
                )
            ).first()
            
            if service:
                service_name = service.name
                service_price = float(service.price)

        # 5. Karta tekshirish (only_card=True bo'lsa)
        if appointment_data.only_card:
            if not appointment_data.payment_card_id:
                raise HTTPException(
                    status_code=400,
                    detail=get_translation(language, "errors.400") or "Karta ID majburiy"
                )
            
            payment_card = db.query(PaymentCard).filter(
                and_(
                    PaymentCard.id == appointment_data.payment_card_id,
                    PaymentCard.is_active == True
                )
            ).first()
            
            if not payment_card:
                raise HTTPException(
                    status_code=404,
                    detail=get_translation(language, "errors.404") or "To'lov kartasi topilmadi"
                )

        # 6. Vaqt tekshirish (schedule vaqt oralig'ida bo'lishi kerak)
        if schedule.start_time and schedule.end_time:
            if not (schedule.start_time <= appointment_data.application_time <= schedule.end_time):
                raise HTTPException(
                    status_code=400,
                    detail=get_translation(language, "errors.400") or "Vaqt jadval oralig'ida emas"
                )

        # 7. Bir xil vaqtda appointment borligini tekshirish
        existing_appointment = db.query(Appointment).filter(
            and_(
                Appointment.schedule_id == appointment_data.schedule_id,
                Appointment.employee_id == appointment_data.employee_id,
                Appointment.application_date == appointment_data.application_date,
                Appointment.application_time == appointment_data.application_time,
                Appointment.is_cancelled == False
            )
        ).first()
        
        if existing_appointment:
            raise HTTPException(
                status_code=409,
                detail=get_translation(language, "errors.409") or "Bu vaqtda allaqachon appointment mavjud"
            )

        # 8. Application number yaratish
        application_number = f"APP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        # 9. Appointment yaratish
        new_appointment = Appointment(
            application_number=application_number,
            user_name=appointment_data.user_name,
            phone_number=appointment_data.phone_number,
            application_date=appointment_data.application_date,
            application_time=appointment_data.application_time,
            schedule_id=appointment_data.schedule_id,
            employee_id=appointment_data.employee_id,
            service_name=service_name,
            service_price=service_price,
            status="pending",
            notes=appointment_data.notes,
            is_confirmed=False,
            is_completed=False,
            is_cancelled=False
        )

        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)

        return MobileAppointmentResponse(
            success=True,
            message=get_translation(language, "success.appointment_created") or "Appointment muvaffaqiyatli yaratildi",
            appointment_id=str(new_appointment.id),
            application_number=new_appointment.application_number
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error creating appointment: {e}")
        raise HTTPException(
            status_code=500,
            detail=get_translation(language, "errors.500") or "Server xatosi"
        )
#     employee = db.query(Employee).filter(Employee.id == employee_id).first()
    
#     return MobileScheduleServiceItem(
#         id=str(schedule.id),
#         salon_id=str(schedule.salon_id),
#         name=schedule.name,
#         title=schedule.title,
#         price=float(schedule.price) if schedule.price is not None else 0.0,
#         date=str(schedule.date) if schedule.date else None,
#         day=_weekday_short(schedule.date) if schedule.date else None,
#         employees=[
#             {
#                 "id": employee_id,
#                 "name": (
#                     employee.name if employee and employee.name else "Unknown"
#                 ),
#                 "avatar": employee.avatar_url,  # Placeholder, replace with actual avatar URL if available
#                 "workType": employee.profession,  # Placeholder, replace with actual work type if available
#                 "rate": employee.rating,  # Placeholder, replace with actual rating if available
#                 "reviewsCount": 0,
#             }
#         ],
#         times=slots,
#         onlyCard=False,
#     )

