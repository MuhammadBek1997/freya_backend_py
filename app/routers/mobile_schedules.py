from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Union
from datetime import date, datetime, time, timedelta
from pydantic import BaseModel, ConfigDict, Field, field_validator
import uuid

from app.auth.dependencies import get_current_user, get_current_user_optional
from app.database import get_db
from app.i18nMini import get_translation
from app.models.salon import Salon
from app.models.schedule import Schedule
from app.models.employee import Employee, EmployeeComment
from app.models.appointment import Appointment
from app.models.payment_card import PaymentCard
from app.models.service import Service
from app.models.user import User
from app.schemas.schedule_mobile import (
    MobileScheduleListResponse,
    MobileScheduleServiceItem,
    MobileScheduleFiltersResponse,
    MobileScheduleFilters,
    MobileScheduleDailyFiltersItem,
    MobileScheduleDailyFiltersResponse,
    DailyEmployeeItem,
    MobileEmployeeWeeklyResponse,
    MobileEmployeeWeeklyDayItem,
    MobileEmployeeDayServicesItem,
)


# Appointment yaratish uchun schema'lar
class MobileAppointmentCreate(BaseModel):
    salon_id: str
    schedule_id: Optional[str] = None  # Service model'dan
    # schedule_id: str
    employee_id: str
    application_date: Optional[date] = Field(None, alias="date")
    application_time: time = Field(alias="time")

    @field_validator("application_time", mode="before")
    def _validate_hhmm_time(cls, v):
        if isinstance(v, str):
            # Faqat HH:MM formatiga ruxsat
            import re
            if not re.fullmatch(r"\d{2}:\d{2}", v):
                raise ValueError("time HH:MM formatida bo'lishi kerak")
            from datetime import datetime as _dt
            return _dt.strptime(v, "%H:%M").time()
        return v
    # user_name: Optional[str] = None
    # phone_number: Optional[str] = None
    only_card: bool = False
    payment_card_id: Optional[str] = None  # only_card=True bo'lsa majburiy
    # notes: Optional[str] = None

    # Swagger example (Pydantic v2)
    # model_config = ConfigDict(populate_by_name=True, json_schema_extra={
    #     "example": {
    #         "salon_id": "4302cd19-0f0e-4182-afaa-8dd152d0ed8d",
    #         "service_id": None,
    #         # "schedule_id": "e78d69da-833d-4a1d-83e2-648b671b3085",
    #         "employee_id": "4a8f338a-d03e-42a1-93b6-ba73d0cb0dbb",
    #         # "date": "2025-10-07",
    #         "application_time": "11:52",
    #         # "user_name": "Booknow Tester",
    #         # "phone_number": "+998901234567",
    #         "only_card": False,
    #         "payment_card_id": None,
    #         # "notes": "booknow test"
    #     }
    # })


class MobileBookedAppointmentItem(BaseModel):
    id: str
    application_number: str
    application_date: str
    application_time: str
    employee_id: Optional[str] = None
    service_name: str
    status: str
    is_confirmed: bool = False
    is_completed: bool = False
    is_cancelled: bool = False

    # Swagger example for an item
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "d1afd36a-62bb-4706-810b-b7743b5808ab",
                "application_number": "APP-20251019-F76742BB",
                "application_date": "2025-10-07",
                "application_time": "11:52",
                "employee_id": "4a8f338a-d03e-42a1-93b6-ba73d0cb0dbb",
                "service_name": "22",
                "status": "pending",
                "is_confirmed": False,
                "is_completed": False,
                "is_cancelled": False,
            }
        }
    )


class MobileAppointmentResponse(BaseModel):
    success: bool
    message: str
    appointment_id: Optional[str] = None
    application_number: Optional[str] = None
    bookedAppointments: Optional[List[MobileBookedAppointmentItem]] = []

    # Swagger example for response
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Appointment muvaffaqiyatli yaratildi",
                "appointment_id": "d1afd36a-62bb-4706-810b-b7743b5808ab",
                "application_number": "APP-20251019-F76742BB",
                "bookedAppointments": [
                    {
                        "id": "d1afd36a-62bb-4706-810b-b7743b5808ab",
                        "application_number": "APP-20251019-F76742BB",
                        "application_date": "2025-10-07",
                        "application_time": "11:52",
                        "employee_id": "4a8f338a-d03e-42a1-93b6-ba73d0cb0dbb",
                        "service_name": "22",
                        "status": "pending",
                        "is_confirmed": False,
                        "is_completed": False,
                        "is_cancelled": False,
                    }
                ],
            }
        }
    )


router = APIRouter(prefix="/mobile/schedules", tags=["Mobile Schedules"])


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


def _weekday_short(d: date) -> Optional[str]:
    if not d:
        return None
    weekdays = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    try:
        return weekdays[d.weekday()]
    except Exception:
        return None


@router.get(
    "/filters/{salon_id}",
    response_model=MobileScheduleDailyFiltersResponse,
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
    start_date: str = Query(
        ...,
        description="YYYY-MM-DD formatida boshlang'ich sana (7 kunlik interval uchun)",
    ),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Mobil UI uchun 7 kunlik (har kun uchun) jadval filtrlari: yo'nalishlar, vaqt oraliqlari, xodimlar"""

    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    # Boshlang'ich sanani tekshirish va 7 kunlik oraliqni hisoblash
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD",
        )
    end_dt = start_dt + timedelta(days=6)

    # 7 kunlik har kun uchun alohida ro'yxat tayyorlash
    daily_items: List[MobileScheduleDailyFiltersItem] = []
    day_iter = start_dt
    while day_iter <= end_dt:
        day_schedules: List[Schedule] = (
            db.query(Schedule)
            .filter(Schedule.salon_id == salon_id)
            .filter(Schedule.is_active == True)
            .filter(Schedule.date == day_iter)
            .order_by(Schedule.start_time.asc())
            .all()
        )

        # Directions
        day_directions: List[str] = sorted({s.name for s in day_schedules if s.name})

        # Times

        # Employees
        employee_ids: List[str] = []
        for s in day_schedules:
            if s.employee_list:
                employee_ids.extend([str(eid) for eid in s.employee_list])
        employee_ids = list(sorted(set(employee_ids)))
        day_employees: List[DailyEmployeeItem] = []
        if employee_ids:
            for e in db.query(Employee).filter(Employee.id.in_(employee_ids)).all():
                emp_name = getattr(e, "full_name", None) or getattr(e, "name", None)
                day_employees.append(DailyEmployeeItem(id=str(e.id), name=emp_name))

        daily_items.append(
            MobileScheduleDailyFiltersItem(
                date=str(day_iter),
                avialable=(len(day_schedules) > 0),
                directions=day_directions,
                employees=day_employees,
            )
        )

        day_iter += timedelta(days=1)

    return MobileScheduleDailyFiltersResponse(
        success=True,
        data=daily_items,
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

    def get_emp(eid: str) -> dict:
        if not eid:
            return {
                "id": "",
                "name": None,
                "avatar": None,
                "workType": None,
                "rate": 0.0,
                "reviewsCount": 0,
                "works": 0,
                "perWeek": 0,
            }
        if eid in emp_cache:
            return emp_cache[eid]
        emp = db.query(Employee).filter(Employee.id == eid).first()
        # Reviews count
        try:
            reviews_cnt = (
                db.query(func.count(EmployeeComment.id))
                .filter(EmployeeComment.employee_id == eid)
                .scalar()
                or 0
            )
        except Exception:
            reviews_cnt = 0
        # Total works (appointments done)
        try:
            works_total = (
                db.query(func.count(Appointment.id))
                .filter(
                    and_(Appointment.employee_id == eid, Appointment.status == "done")
                )
                .scalar()
                or 0
            )
        except Exception:
            works_total = 0
        # Weekly works (appointments done in the selected week)
        try:
            works_week = 0
        except Exception:
            works_week = 0

        employee_item = {
            "id": str(eid),
            "name": (emp.name if emp and getattr(emp, "name", None) else None),
            "avatar": (
                emp.avatar_url if emp and getattr(emp, "avatar_url", None) else None
            ),
            "workType": (
                emp.profession if emp and getattr(emp, "profession", None) else None
            ),
            "rate": (
                float(emp.rating)
                if emp and getattr(emp, "rating", None) is not None
                else 0.0
            ),
            "reviewsCount": int(reviews_cnt),
            "works": int(works_total),
            "perWeek": int(works_week),
        }
        emp_cache[eid] = employee_item
        return employee_item

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


@router.get("/user/{user_id}/appointments")
async def get_appointments_by_user_id(
    user_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Get appointments by user_id"""
    offset = (page - 1) * limit

    query = db.query(Appointment).filter(Appointment.user_id == user_id)
    count_query = db.query(func.count(Appointment.id)).filter(Appointment.user_id == user_id)

    if status:
        query = query.filter(Appointment.status == status)
        count_query = count_query.filter(Appointment.status == status)

    total = count_query.scalar() or 0
    appointments = query.order_by(Appointment.application_date.desc()).offset(offset).limit(limit).all()

    return {
        "success": True,
        "message": get_translation(language, "success"),
        "data": appointments,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if limit else 1,
        },
    }

@router.post("/appointments", response_model=MobileAppointmentResponse)
async def create_appointment(
    appointment_data: MobileAppointmentCreate,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Yangi appointment yaratish - salon, servis, vaqt, employee va karta tekshirish bilan"""
    try:
        # 1. Salon mavjudligini tekshirish
        salon = (
            db.query(Salon)
            .filter(
                and_(Salon.id == appointment_data.salon_id, Salon.is_active == True)
            )
            .first()
        )

        if not salon:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404") or "Salon topilmadi",
            )

        # 2. Schedule mavjudligini tekshirish
        schedule = (
            db.query(Schedule)
            .filter(
                and_(
                    Schedule.id == appointment_data.schedule_id,
                    Schedule.salon_id == appointment_data.salon_id,
                    Schedule.is_active == True,
                )
            )
            .first()
        )

        if not schedule:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404") or "Jadval topilmadi",
            )
        # resolved_date: kiritilmasa schedule.date olinadi
        resolved_date = appointment_data.application_date or schedule.date
        if resolved_date is None:
            raise HTTPException(
                status_code=400,
                detail=get_translation(language, "errors.400") or "Sana kiritilmagan va jadvalda sana mavjud emas",
            )
        # Tanlangan vaqt majburiy
        selected_time = appointment_data.application_time
        if selected_time is None:
            raise HTTPException(
                status_code=400,
                detail=get_translation(language, "errors.400") or "Vaqt kiritilmagan va jadvalda boshlanish vaqti mavjud emas",
            )

        # 3. Employee mavjudligini va schedule'da borligini tekshirish
        employee = (
            db.query(Employee)
            .filter(
                and_(
                    Employee.id == appointment_data.employee_id,
                    Employee.salon_id == appointment_data.salon_id,
                    Employee.is_active == True,
                )
            )
            .first()
        )

        if not employee:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404") or "Xodim topilmadi",
            )

        # 4. Service mavjudligini tekshirish (agar berilgan bo'lsa)
        service_name = schedule.name
        service_price = float(schedule.price)

        # 5. Karta tekshirish (only_card=True bo'lsa)
        if appointment_data.only_card:
            if not appointment_data.payment_card_id:
                raise HTTPException(
                    status_code=400,
                    detail=get_translation(language, "errors.400")
                    or "Karta ID majburiy",
                )

            payment_card = (
                db.query(PaymentCard)
                .filter(
                    and_(
                        PaymentCard.id == appointment_data.payment_card_id,
                        PaymentCard.is_active == True,
                    )
                )
                .first()
            )

            if not payment_card:
                raise HTTPException(
                    status_code=404,
                    detail=get_translation(language, "errors.404")
                    or "To'lov kartasi topilmadi",
                )

        # 6. Vaqt tekshirish (schedule vaqt oralig'ida bo'lishi kerak)
        if schedule.start_time and schedule.end_time:
            if not (schedule.start_time <= selected_time <= schedule.end_time):
                raise HTTPException(
                    status_code=400,
                    detail=get_translation(language, "errors.400") or "Vaqt jadval oralig'ida emas",
                )

        # 7. Bir xil vaqtda appointment borligini tekshirish
        existing_appointment = (
            db.query(Appointment)
            .filter(
                and_(
                    Appointment.employee_id == appointment_data.employee_id,
                    Appointment.application_date == resolved_date,
                    Appointment.application_time == selected_time,
                    Appointment.is_cancelled == False,
                )
            )
            .first()
        )

        if existing_appointment:
            raise HTTPException(
                status_code=409,
                detail=get_translation(language, "errors.409")
                or "Bu vaqtda allaqachon appointment mavjud",
            )

        # 8. Application number yaratish
        application_number = (
            f"APP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        )

        # 9. Appointment yaratish
        new_appointment = Appointment(
            application_number=application_number,
            user_name=(current_user.full_name if current_user and current_user.full_name else ""),
            phone_number=(current_user.phone if current_user and current_user.phone else ""),
            application_date=resolved_date,
            application_time=selected_time,
            employee_id=appointment_data.employee_id,
            service_name=service_name,
            service_price=service_price,
            status="pending",
            is_confirmed=False,
            is_completed=False,
            is_cancelled=False,
        )

        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)

        booked_q = []
        if current_user and current_user.phone:
            booked_q = (
                db.query(Appointment)
                .filter(
                    and_(
                        Appointment.phone_number == current_user.phone,
                        Appointment.is_cancelled == False,
                    )
                )
                .order_by(
                    Appointment.application_date.desc(),
                    Appointment.application_time.desc(),
                )
                .limit(10)
                .all()
            )

        booked_items = [
            MobileBookedAppointmentItem(
                id=str(a.id),
                application_number=a.application_number,
                application_date=(
                    a.application_date.isoformat() if a.application_date else None
                ),
                application_time=(
                    a.application_time.strftime("%H:%M") if a.application_time else None
                ),
                employee_id=(str(a.employee_id) if a.employee_id else None),
                service_name=a.service_name,
                status=a.status or "pending",
                is_confirmed=bool(a.is_confirmed),
                is_completed=bool(a.is_completed),
                is_cancelled=bool(a.is_cancelled),
            )
            for a in booked_q
        ]

        return MobileAppointmentResponse(
            success=True,
            message=get_translation(language, "success.appointment_created")
            or "Appointment muvaffaqiyatli yaratildi",
            appointment_id=str(new_appointment.id),
            application_number=new_appointment.application_number,
            bookedAppointments=booked_items,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error creating appointment: {e}")
        raise HTTPException(
            status_code=500,
            detail=get_translation(language, "errors.500") or "Server xatosi",
        )


@router.get(
    "/employee/{employee_id}",
    response_model=MobileEmployeeWeeklyResponse,
    summary="Mobil: Xodim bo'yicha 1 haftalik jadval",
    description="X-User-language (uz|ru|en) headeri bo'yicha ko'p tilli misollar",
)
async def get_mobile_schedules_by_employee(
    employee_id: str,
    start_date: str = Query(
        ...,
        description="YYYY-MM-DD formatida boshlang'ich sana (7 kunlik interval uchun)",
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(7, ge=1, le=7),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    try:
        start_dt = date.fromisoformat(start_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid start_date format. Use YYYY-MM-DD",
        )

    total_days = 7
    end_dt = start_dt + timedelta(days=total_days - 1)

    schedules = (
        db.query(Schedule)
        .filter(
            Schedule.date >= start_dt,
            Schedule.date <= end_dt,
            Schedule.is_active == True,
        )
        .order_by(Schedule.date.asc(), Schedule.start_time.asc())
        .all()
    )

    services_by_date = {}

    def _has_employee(emp_list, eid: str) -> bool:
        if not emp_list:
            return False
        try:
            if isinstance(emp_list, list):
                return any(str(x) == str(eid) for x in emp_list)
            if isinstance(emp_list, str):
                return str(eid) in emp_list
        except Exception:
            return False
        return False

    for s in schedules:
        if not _has_employee(s.employee_list, employee_id):
            continue
        day_key = s.date
        if not day_key:
            continue
        if day_key not in services_by_date:
            services_by_date[day_key] = []
        services_by_date[day_key].append(
            {
                "id": str(s.id),
                "salon_id": str(s.salon_id),
                "name": s.name,
                "title": s.title,
                "price": float(s.price) if s.price is not None else 0.0,
                "day": _weekday_short(s.date) if s.date else None,
                "start_time": (
                    s.start_time.strftime("%H:%M") if s.start_time else None
                ),
                "end_time": (s.end_time.strftime("%H:%M") if s.end_time else None),
            }
        )

    emp_cache = {}

    def get_emp(eid: str) -> dict:
        if not eid:
            return {
                "id": "",
                "name": None,
                "avatar": None,
                "workType": None,
                "rate": 0.0,
                "reviewsCount": 0,
            }
        if eid in emp_cache:
            return emp_cache[eid]
        emp = db.query(Employee).filter(Employee.id == eid).first()
        try:
            reviews_cnt = (
                db.query(func.count(EmployeeComment.id))
                .filter(EmployeeComment.employee_id == eid)
                .scalar()
                or 0
            )
        except Exception:
            reviews_cnt = 0
        try:
            works_total = (
                db.query(func.count(Appointment.id))
                .filter(
                    and_(Appointment.employee_id == eid, Appointment.status == "done")
                )
                .scalar()
                or 0
            )
        except Exception:
            works_total = 0
        try:
            works_week = (
                db.query(func.count(Appointment.id))
                .filter(
                    and_(
                        Appointment.employee_id == eid,
                        Appointment.status == "done",
                        Appointment.application_date >= start_dt,
                        Appointment.application_date <= end_dt,
                    )
                )
                .scalar()
                or 0
            )
        except Exception:
            works_week = 0
        employee_item = {
            "id": str(eid),
            "name": (emp.name if emp and getattr(emp, "name", None) else None),
            "avatar": (
                emp.avatar_url if emp and getattr(emp, "avatar_url", None) else None
            ),
            "workType": (
                emp.profession if emp and getattr(emp, "profession", None) else None
            ),
            "rate": (
                float(emp.rating)
                if emp and getattr(emp, "rating", None) is not None
                else 0.0
            ),
            "reviewsCount": int(reviews_cnt),
            "works": int(works_total),
            "perWeek": int(works_week),
        }
        emp_cache[eid] = employee_item
        return employee_item

    target_employee = get_emp(employee_id)

    all_days = []
    for i in range(total_days):
        d = start_dt + timedelta(days=i)
        day_services = services_by_date.get(d, [])
        all_days.append(
            {
                "date": d.isoformat(),
                "avialable": bool(day_services),
                "services": day_services,
            }
        )

    total = len(all_days)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paged_days = all_days[start_idx:end_idx]
    pages = (total + limit - 1) // limit if limit else 0

    return MobileEmployeeWeeklyResponse(
        success=True,
        data=paged_days,
        employee=target_employee,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": pages,
        },
    )
