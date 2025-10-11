import math
from fastapi import APIRouter, Depends, HTTPException, Header, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from typing import List, Optional, Union
from datetime import date, timedelta, datetime

from app.database import get_db
from app.i18nMini import get_translation
from app.models.employee import Employee, EmployeeComment, EmployeePost
from app.models.salon import Salon
from app.models.schedule import Schedule
from app.schemas.employee import MobileEmployeeListResponse, MobileEmployeeItem, MobileEmployeeDetailResponse
from app.schemas.salon import MobileSalonItem
from app.models.appointment import Appointment
from app.models.user_favourite_salon import UserFavouriteSalon


# Schema'lar kun bo'yicha xodimlar ish jadvali uchun
class EmployeeScheduleItem(BaseModel):
    employee_id: str
    employee_name: str
    service_name: str
    service_type: Optional[str] = None
    is_private: bool
    time: str  # "09:00-18:00" formatida

class DailyEmployeeScheduleResponse(BaseModel):
    success: bool
    date: str  # "2024-01-15" formatida
    data: List[EmployeeScheduleItem]
    pagination: dict


router = APIRouter(prefix="/mobile/employees", tags=["Mobile Employees"])


@router.get(
    "/salon/{salon_id}",
    response_model=MobileEmployeeListResponse,
    summary="Mobil: Salon xodimlari ro'yxati",
    description="X-User-language (uz|ru|en) headeri bo'yicha UI uchun ko'rsatma misollar beriladi.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "uz": {
                            "summary": "Uzbek example",
                            "value": {
                                "success": True,
                                "data": [
                                    {
                                        "id": "emp_001",
                                        "name": "Anna Sergeyeva",
                                        "avatar": "https://cdn.example.com/avatars/emp_001.jpg",
                                        "workType": "Massajchi",
                                        "rate": 4.8,
                                        "reviewsCount": 127
                                    },
                                    {
                                        "id": "emp_002",
                                        "name": "Sara Ahmedova",
                                        "avatar": "https://cdn.example.com/avatars/emp_002.jpg",
                                        "workType": "Manual terapevt",
                                        "rate": 4.6,
                                        "reviewsCount": 89
                                    }
                                ],
                                "pagination": {"page": 1, "limit": 10, "total": 37, "pages": 4}
                            }
                        },
                        "ru": {
                            "summary": "Russian example",
                            "value": {
                                "success": True,
                                "data": [
                                    {
                                        "id": "emp_001",
                                        "name": "Анна Сергеева",
                                        "avatar": "https://cdn.example.com/avatars/emp_001.jpg",
                                        "workType": "Массажист",
                                        "rate": 4.8,
                                        "reviewsCount": 127
                                    },
                                    {
                                        "id": "emp_002",
                                        "name": "Сара Ахмедова",
                                        "avatar": "https://cdn.example.com/avatars/emp_002.jpg",
                                        "workType": "Мануальный терапевт",
                                        "rate": 4.6,
                                        "reviewsCount": 89
                                    }
                                ],
                                "pagination": {"page": 1, "limit": 10, "total": 37, "pages": 4}
                            }
                        },
                        "en": {
                            "summary": "English example",
                            "value": {
                                "success": True,
                                "data": [
                                    {
                                        "id": "emp_001",
                                        "name": "Anna Sergeeva",
                                        "avatar": "https://cdn.example.com/avatars/emp_001.jpg",
                                        "workType": "Masseur",
                                        "rate": 4.8,
                                        "reviewsCount": 127
                                    },
                                    {
                                        "id": "emp_002",
                                        "name": "Sara Akhmedova",
                                        "avatar": "https://cdn.example.com/avatars/emp_002.jpg",
                                        "workType": "Manual therapist",
                                        "rate": 4.6,
                                        "reviewsCount": 89
                                    }
                                ],
                                "pagination": {"page": 1, "limit": 10, "total": 37, "pages": 4}
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_employees_by_salon_mobile(
    salon_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Berilgan salon uchun xodimlar ro'yxati.

    Response format:
    - id: string
    - name: string
    - avatar: string (avatar_url)
    - workType: string (profession)
    - rate: float (rating)
    - reviewsCount: int (employee comments count)
    """

    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    # Total employees count (active ones)
    total = (
        db.query(func.count(Employee.id))
        .filter(Employee.salon_id == salon_id, Employee.is_active == True)
        .scalar()
    ) or 0

    # Pagination
    offset = (page - 1) * limit

    employees: List[Employee] = (
        db.query(Employee)
        .filter(Employee.salon_id == salon_id, Employee.is_active == True)
        .order_by(Employee.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    if not employees:
        return MobileEmployeeListResponse(
            success=True,
            data=[],
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit,
            },
        )

    # Preload review counts per employee in one query
    counts = (
        db.query(EmployeeComment.employee_id, func.count(EmployeeComment.id))
        .filter(EmployeeComment.employee_id.in_([e.id for e in employees]))
        .group_by(EmployeeComment.employee_id)
        .all()
    )
    count_map = {emp_id: int(cnt or 0) for emp_id, cnt in counts}

    def _full_name(e: Employee) -> str:
        if e.surname:
            return f"{e.name} {e.surname}".strip()
        return e.name or ""

    items: List[MobileEmployeeItem] = [
        MobileEmployeeItem(
            id=str(e.id),
            name=_full_name(e),
            avatar=e.avatar_url,
            workType=e.profession,
            rate=float(e.rating) if e.rating is not None else 0.0,
            reviewsCount=count_map.get(e.id, 0),
        )
        for e in employees
    ]

    return MobileEmployeeListResponse(
        success=True,
        data=items,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    )


@router.get(
    "/{employee_id}",
    response_model=MobileEmployeeDetailResponse,
    summary="Mobil: Xodim batafsil",
    description="X-User-language (uz|ru|en) headeri bo'yicha salon tavsifi va nomlar misollari ko'rsatiladi.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "uz": {
                            "summary": "Uzbek example",
                            "value": {
                                "id": "emp_001",
                                "name": "Anna Sergeyeva",
                                "avatar": "https://cdn.example.com/avatars/emp_001.jpg",
                                "position": "Massajchi",
                                "works": 112,
                                "reviews_count": 27,
                                "per_week": 6,
                                "salon": {
                                    "id": "sal_001",
                                    "name": "GLAMFACE",
                                    "description": "Qulay joylashuv, tajribali ustozlar va shinam muhit.",
                                    "logo": "https://cdn.example.com/salons/sal_001/logo.jpg",
                                    "salonImage": "https://cdn.example.com/salons/sal_001/cover.jpg",
                                    "city": "Toshkent, Yunusobod",
                                    "rate": 4.8,
                                    "reviews": 127,
                                    "news": ["new", "top", "discount-20%"],
                                    "isFavorite": True
                                }
                            }
                        },
                        "ru": {
                            "summary": "Russian example",
                            "value": {
                                "id": "emp_001",
                                "name": "Анна Сергеева",
                                "avatar": "https://cdn.example.com/avatars/emp_001.jpg",
                                "position": "Массажист",
                                "works": 112,
                                "reviews_count": 27,
                                "per_week": 6,
                                "salon": {
                                    "id": "sal_001",
                                    "name": "GLAMFACE",
                                    "description": "Удобное расположение, опытные мастера и уютная атмосфера.",
                                    "logo": "https://cdn.example.com/salons/sal_001/logo.jpg",
                                    "salonImage": "https://cdn.example.com/salons/sal_001/cover.jpg",
                                    "city": "Ташкент, Юнусабад",
                                    "rate": 4.8,
                                    "reviews": 127,
                                    "news": ["new", "top", "discount-20%"],
                                    "isFavorite": True
                                }
                            }
                        },
                        "en": {
                            "summary": "English example",
                            "value": {
                                "id": "emp_001",
                                "name": "Anna Sergeeva",
                                "avatar": "https://cdn.example.com/avatars/emp_001.jpg",
                                "position": "Masseur",
                                "works": 112,
                                "reviews_count": 27,
                                "per_week": 6,
                                "salon": {
                                    "id": "sal_001",
                                    "name": "GLAMFACE",
                                    "description": "Convenient location, experienced masters and cozy ambience.",
                                    "logo": "https://cdn.example.com/salons/sal_001/logo.jpg",
                                    "salonImage": "https://cdn.example.com/salons/sal_001/cover.jpg",
                                    "city": "Tashkent, Yunusabad",
                                    "rate": 4.8,
                                    "reviews": 127,
                                    "news": ["new", "top", "discount-20%"],
                                    "isFavorite": True
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_employee_by_id_mobile(
    employee_id: str,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    """
    Xodim ID bo'yicha batafsil ma'lumot (mobile format):
    {
      "id", "name", "avatar", "position", "works", "reviews_count", "per_week",
      "salon": { "id", "name", "description", "logo", "salonImage", "city", "rate", "reviews", "news", "isFavorite" }
    }
    """

    # Xodimni tekshirish
    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id, Employee.is_active == True, Employee.deleted_at.is_(None))
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    # Salonni olish
    salon = db.query(Salon).filter(Salon.id == employee.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    # Ishlar soni (yakunlangan appointmentlar)
    works = (
        db.query(func.count(Appointment.id))
        .filter(Appointment.employee_id == employee_id, Appointment.status == "done")
        .scalar()
    ) or 0

    # Haftalik ishlar soni (so'nggi 7 kun)
    start = date.today() - timedelta(days=6)
    end = date.today()
    per_week = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.employee_id == employee_id,
            Appointment.status == "done",
            Appointment.application_date >= start,
            Appointment.application_date <= end,
        )
        .scalar()
    ) or 0

    # Sharhlar soni
    reviews_count = (
        db.query(func.count(EmployeeComment.id))
        .filter(EmployeeComment.employee_id == employee_id)
        .scalar()
    ) or 0

    # Salon descriptionni til bo'yicha tanlash
    description = None
    if language:
        lang = language.lower()
        if lang in ["uz", "ru", "en"]:
            description = getattr(salon, f"description_{lang}", None)
    if not description:
        # fallback: umumiy yoki mavjud matnlar
        description = getattr(salon, "salon_description", None) or salon.description_uz or salon.description_ru or salon.description_en

    # Rasm va shahar
    photos = getattr(salon, "photos", None) or []
    logo = photos[0] if len(photos) > 0 else getattr(salon, "logo", None)
    salon_image = photos[1] if len(photos) > 1 else (photos[0] if len(photos) > 0 else None)
    city = None
    for addr in [getattr(salon, "address_uz", None), getattr(salon, "address_ru", None), getattr(salon, "address_en", None)]:
        if addr and isinstance(addr, str):
            city = addr.strip()
            break

    # Reyting va umumiy sharhlar soni (salon bo'yicha)
    rate = float(salon.salon_rating) if salon.salon_rating is not None else 0.0
    salon_reviews = (
        db.query(func.count(EmployeeComment.id))
        .join(Employee, EmployeeComment.employee_id == Employee.id)
        .filter(Employee.salon_id == salon.id)
        .scalar()
    ) or 0

    # Yangiliklar teglarini shakllantirish
    news: List[str] = []
    try:
        from datetime import datetime, timedelta as _td
        if salon.created_at and salon.created_at >= datetime.utcnow() - _td(days=14):
            news.append("new")
        if getattr(salon, "is_top", False):
            news.append("top")
        sale = salon.salon_sale
        if isinstance(sale, dict):
            percent = sale.get("percent") or sale.get("percentage")
            if isinstance(percent, (int, float)) and percent > 0:
                news.append(f"discount-{int(percent)}%")
        elif isinstance(sale, (int, float)) and sale > 0:
            news.append(f"discount-{int(sale)}%")
        elif isinstance(sale, str):
            import re
            m = re.search(r"(\d{1,2})", sale)
            if m:
                try:
                    num = int(m.group(1))
                    news.append(f"discount-{num}%")
                except Exception:
                    pass
    except Exception:
        pass

    # Favorite flag (foydalanuvchi bergan userId bo'yicha)
    is_fav = False
    try:
        if userId:
            is_fav = (
                db.query(UserFavouriteSalon)
                .filter(UserFavouriteSalon.user_id == userId, UserFavouriteSalon.salon_id == str(salon.id))
                .first()
                is not None
            )
    except Exception:
        is_fav = False

    # To‘liq javob
    full_name = (f"{employee.name} {employee.surname}" if employee.surname else (employee.name or "")).strip()
    return MobileEmployeeDetailResponse(
        id=str(employee.id),
        name=full_name,
        avatar=employee.avatar_url,
        phone=employee.phone,
        position=employee.profession,
        works=int(works),
        reviews_count=int(reviews_count),
        per_week=int(per_week),
        salon=MobileSalonItem(
            id=str(salon.id),
            name=salon.salon_name,
            description=description,
            logo=logo,
            salonImage=salon_image,
            city=city,
            rate=rate,
            reviews=int(salon_reviews),
            news=news,
            isFavorite=is_fav,
        ),
    )


class EmployeePostListResponse(BaseModel):
    success: bool
    data: List[dict]
    pagination: dict


@router.get("/{employee_id}/posts", response_model=EmployeePostListResponse)
async def get_employee_posts(
    employee_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Get employee posts with pagination"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404")
            )
        
        offset = (page - 1) * limit
        
        # Get total count
        total_query = db.query(func.count(EmployeePost.id)).filter(EmployeePost.employee_id == employee_id)
        total = total_query.count() or 0
        
        # Get paginated results
        posts_query = db.query(EmployeePost).filter(EmployeePost.employee_id == employee_id).order_by(desc(EmployeePost.created_at))
        posts = posts_query.offset(offset).limit(limit).all()
        
        # Format response
        formatted_posts = []
        for post in posts:
            post_dict = {
                "id": str(post.id),
                "employee_id": str(post.employee_id),
                "title": post.title,
                "description": post.description,
                "is_active": post.is_active,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
            }
            formatted_posts.append(post_dict)
        
        return EmployeePostListResponse(
            success=True,
            data=formatted_posts,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": math.ceil(total / limit),
            },
        )
    except Exception as e:
        print(f"Error fetching employee posts: {e}, traceback: {e.__traceback__.tb_lineno}")
        return HTTPException(
            status_code=500,
            detail=get_translation(language, "errors.500")
        )


@router.get("/schedules/{date}", response_model=DailyEmployeeScheduleResponse)
async def get_employee_schedules_by_date(
    date: str,  # "2024-01-15" formatida
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Berilgan kun bo'yicha barcha xodimlarning ish jadvalini qaytaradi"""
    try:
        # Date'ni parse qilish
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=get_translation(language, "errors.400") or "Invalid date format. Use YYYY-MM-DD"
            )

        # O'sha kun uchun barcha schedule'larni olish
        schedules = db.query(Schedule).filter(
            and_(
                Schedule.date == target_date,
                Schedule.is_active == True
            )
        ).all()

        # Har bir schedule uchun employee ma'lumotlarini olish
        employee_schedules = []
        for schedule in schedules:
            if schedule.employee_list:
                for employee_id in schedule.employee_list:
                    # Employee ma'lumotlarini olish
                    employee = db.query(Employee).filter(
                        and_(
                            Employee.id == employee_id,
                            Employee.is_active == True
                        )
                    ).first()
                    
                    if employee:
                        # Salon ma'lumotlarini olish (is_private uchun)
                        salon = db.query(Salon).filter(Salon.id == schedule.salon_id).first()
                        
                        # Time formatini yaratish
                        start_time = schedule.start_time.strftime("%H:%M") if schedule.start_time else "09:00"
                        end_time = schedule.end_time.strftime("%H:%M") if schedule.end_time else "18:00"
                        time_range = f"{start_time}-{end_time}"
                        
                        employee_schedules.append(EmployeeScheduleItem(
                            employee_id=str(employee.id),
                            employee_name=employee.name or "Unknown",
                            service_name=schedule.name,
                            service_type=employee.profession,
                            is_private=salon.private_salon if salon else False,
                            time=time_range
                        ))

        # Pagination
        total = len(employee_schedules)
        offset = (page - 1) * limit
        paginated = employee_schedules[offset: offset + limit]

        return DailyEmployeeScheduleResponse(
            success=True,
            date=date,
            data=paginated,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if limit else 1,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=get_translation(language, "errors.500"))
