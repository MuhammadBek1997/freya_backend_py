from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Union
from datetime import date, datetime, time, timedelta

from app.database import get_db
from app.i18nMini import get_translation
from app.models.salon import Salon
from app.models.schedule import Schedule
from app.models.employee import Employee
from app.schemas.schedule_mobile import (
    MobileScheduleListResponse,
    MobileScheduleServiceItem,
    MobileScheduleFiltersResponse,
    MobileScheduleFilters,
)


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
                                        "avatar": "https://example.com/anna.jpg"
                                    }
                                ],
                                "times": [
                                    {
                                        "time": "08:00-09:00",
                                        "empty_slot": False
                                    }
                                ],
                                "onlyCard": False
                            }
                        ],
                        "pagination": {
                            "page": 1,
                            "limit": 10,
                            "total": 100,
                            "pages": 10
                        }
                    }
                }
            }
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
                onlyCard=False
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
