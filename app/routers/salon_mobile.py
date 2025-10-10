from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, Union, List
import math
import uuid

from app.database import get_db
from app.i18nMini import get_translation
from app.models.salon import Salon
from app.schemas.salon import MobileSalonItem, MobileSalonDetailResponse, MobileAddressInfo, MobileSalonListResponse
from app.models.employee import Employee, EmployeeComment
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from datetime import datetime, date, timedelta
from app.models.user_favourite_salon import UserFavouriteSalon
from app.models.user import User

router = APIRouter(prefix="/mobile/salons", tags=["Mobile Salons"])

# Default values
DEFAULT_SALON_TYPES = [
    {"type": "beauty_salon", "selected": True},
    {"type": "fitness", "selected": False},
    {"type": "functional_training", "selected": False},
    {"type": "massage", "selected": False},
    {"type": "yoga", "selected": False},
    {"type": "nail_service", "selected": False},
    {"type": "scratching", "selected": False},
    {"type": "pilates", "selected": False},
    {"type": "eyebrow_and_eyelash_shaping", "selected": False},
    {"type": "hair_services", "selected": False},
    {"type": "gyms", "selected": False},
    {"type": "dancing", "selected": False},
    {"type": "body_care", "selected": False},
    {"type": "facial_care", "selected": False},
    {"type": "spa_and_wellness", "selected": False},
    {"type": "swimming_pool", "selected": False},
    {"type": "martial_arts", "selected": False},
    {"type": "entertainment", "selected": False},
    {"type": "meditation", "selected": False},
    {"type": "active_recreation", "selected": False},
    {"type": "water_sports", "selected": False},
    {"type": "gymnastics", "selected": False},
    {"type": "eastern_practices", "selected": False},
    {"type": "foreign_languages", "selected": False},
    {"type": "for_children", "selected": False}
]

DEFAULT_LOCATION = {"lat": 41, "lng": 64}

DEFAULT_SALON_COMFORT = [
    {"name": "parking", "isActive": False},
    {"name": "cafee", "isActive": False},
    {"name": "onlyFemale", "isActive": False},
    {"name": "onlyWoman", "isActive": False},
    {"name": "water", "isActive": False},
    {"name": "pets", "isActive": False},
    {"name": "bath", "isActive": False},
    {"name": "towel", "isActive": False},
    {"name": "kids", "isActive": False}
]

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # km
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def _pick_description(salon: Salon, language: Optional[str]) -> Optional[str]:
    if language:
        lang = language.lower()
        if lang in ["uz", "ru", "en"]:
            val = getattr(salon, f"description_{lang}", None)
            if val:
                return val
    # fallback chain
    return salon.description_uz or salon.description_ru or salon.description_en


def _compose_news(salon: Salon) -> List[str]:
    tags: List[str] = []
    try:
        # New if created within last 14 days
        if salon.created_at:
            from datetime import datetime, timedelta
            if salon.created_at >= datetime.utcnow() - timedelta(days=14):
                tags.append("new")
        if getattr(salon, "is_top", False):
            tags.append("top")
        sale = salon.salon_sale
        if isinstance(sale, dict):
            percent = sale.get("percent") or sale.get("percentage")
            if isinstance(percent, (int, float)) and percent > 0:
                tags.append(f"discount-{int(percent)}%")
        elif isinstance(sale, (int, float)) and sale > 0:
            tags.append(f"discount-{int(sale)}%")
        elif isinstance(sale, str):
            import re
            m = re.search(r"(\d{1,2})", sale)
            if m:
                try:
                    num = int(m.group(1))
                    tags.append(f"discount-{num}%")
                except Exception:
                    pass
    except Exception:
        pass
    return tags


def _is_favourite(db: Session, salon_id: str, user_id: Optional[str]) -> bool:
    if not user_id:
        return False
    try:
        return db.query(UserFavouriteSalon).filter(
            UserFavouriteSalon.user_id == user_id,
            UserFavouriteSalon.salon_id == salon_id
        ).first() is not None
    except Exception:
        return False


def _build_mobile_item(salon: Salon, language: Optional[str], db: Session, user_id: Optional[str]) -> MobileSalonItem:
    description = _pick_description(salon, language) or ""
    # Extract images from photos list for logo/salonImage
    photos = getattr(salon, "photos", None) or []
    logo = photos[0] if len(photos) > 0 else None
    salon_image = photos[1] if len(photos) > 1 else (photos[0] if len(photos) > 0 else None)
    city = None
    # Attempt derive city from address if present
    for addr in [salon.address_uz, salon.address_ru, salon.address_en]:
        if addr and isinstance(addr, str):
            city = addr.strip()
            break

    rate = float(salon.salon_rating) if salon.salon_rating is not None else 0.0
    reviews = 0
    news = _compose_news(salon)
    is_fav = _is_favourite(db, str(salon.id), user_id)

    return MobileSalonItem(
        id=str(salon.id),
        name=salon.salon_name,
        description=description,
        logo=logo,
        salonImage=salon_image,
        city=city,
        rate=rate,
        reviews=reviews,
        news=news,
        isFavorite=is_fav,
    )


def _amenity_flag(salon: Salon, key: str, aliases: List[str] = []) -> bool:
    comforts = getattr(salon, "salon_comfort", None) or []
    try:
        for c in comforts:
            name = (c.get("name") or "").lower()
            is_active = bool(c.get("isActive"))
            if name == key.lower() or name in [a.lower() for a in aliases]:
                return is_active
    except Exception:
        pass
    return False


def _build_mobile_detail(
    salon: Salon,
    language: Optional[str],
    db: Session,
    user_id: Optional[str],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> MobileSalonDetailResponse:
    description = _pick_description(salon, language) or ""
    about = description

    photos = getattr(salon, "photos", None) or []
    logo = photos[0] if len(photos) > 0 else None
    images = photos

    # Address selection by language
    addr_name = None
    if language:
        lang = language.lower()
        if lang in ["uz", "ru", "en"]:
            addr_name = getattr(salon, f"address_{lang}", None)
    if not addr_name:
        addr_name = salon.address_uz or salon.address_ru or salon.address_en

    # Coordinates
    lat = None
    lng = None
    if isinstance(salon.location, dict):
        lat = salon.location.get("lat")
        lng = salon.location.get("lng")

    # Distance
    dist = None
    try:
        if latitude is not None and longitude is not None and lat is not None and lng is not None:
            dist = calculate_distance(float(latitude), float(longitude), float(lat), float(lng))
            dist = round(dist, 2)
    except Exception:
        dist = None

    # News and favorite
    news = _compose_news(salon)
    is_fav = _is_favourite(db, str(salon.id), user_id)

    # Employees images
    emp_images: List[str] = []
    try:
        emp_images = [e.avatar_url for e in db.query(Employee).filter(Employee.salon_id == str(salon.id), Employee.is_active == True).all() if e.avatar_url]
    except Exception:
        emp_images = []

    # Reviews count (sum of employee comments)
    try:
        reviews_count = db.query(func.count(EmployeeComment.id)).join(Employee).filter(Employee.salon_id == str(salon.id)).scalar() or 0
    except Exception:
        reviews_count = 0

    # Dynamic working hours: use today's appointments time range if available
    day_work_time = None
    try:
        today = date.today()
        min_time = (
            db.query(func.min(Appointment.application_time))
            .join(Employee)
            .filter(Employee.salon_id == str(salon.id))
            .filter(Appointment.application_date == today)
            .scalar()
        )
        max_time = (
            db.query(func.max(Appointment.application_time))
            .join(Employee)
            .filter(Employee.salon_id == str(salon.id))
            .filter(Appointment.application_date == today)
            .scalar()
        )
        if min_time and max_time:
            try:
                day_work_time = f"{min_time.strftime('%H:%M')} - {max_time.strftime('%H:%M')}"
            except Exception:
                day_work_time = f"{str(min_time)[:5]} - {str(max_time)[:5]}"
    except Exception:
        day_work_time = None

    # Dynamic week work days: use schedules over next 7 days
    week_work_day = None
    try:
        start = date.today()
        end = start + timedelta(days=6)
        sched_dates = (
            db.query(Schedule.date)
            .filter(Schedule.salon_id == str(salon.id))
            .filter(Schedule.date >= start)
            .filter(Schedule.date <= end)
            .all()
        )
        weekdays = sorted({d[0].weekday() for d in sched_dates if d and d[0]})
        names = [
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
        ]
        if weekdays:
            week_work_day = ",".join(names[i] for i in weekdays)
    except Exception:
        week_work_day = None

    # Amenities mapping with aliases
    parking = _amenity_flag(salon, "parking")
    water = _amenity_flag(salon, "water")
    coffee = _amenity_flag(salon, "coffee", aliases=["cafee"])
    pets = _amenity_flag(salon, "pets")
    shower = _amenity_flag(salon, "shower", aliases=["bath"]) 
    towel = _amenity_flag(salon, "towel")
    children_service = _amenity_flag(salon, "children_service", aliases=["kids"]) 
    only_women = _amenity_flag(salon, "onlyWomen", aliases=["onlyFemale"]) 

    # Nearby metro station from orientation fields if present
    metro = None
    if language:
        lang = language.lower()
        if lang in ["uz", "ru", "en"]:
            metro = getattr(salon, f"orientation_{lang}", None)
    if not metro:
        metro = salon.orientation_uz or salon.orientation_ru or salon.orientation_en

    # Phones
    phones: List[str] = []
    if salon.salon_phone:
        phones = [salon.salon_phone]

    rate = float(salon.salon_rating) if salon.salon_rating is not None else 0.0

    # Qo'shimcha hisoblar: xizmat ko'rsatilgan odamlar va xodimlar soni
    try:
        served_users_count = db.query(func.count(Appointment.id)) \
            .join(Employee, Appointment.employee_id == Employee.id) \
            .filter(Employee.salon_id == salon.id, Appointment.status == 'done') \
            .scalar() or 0
    except Exception:
        served_users_count = 0

    try:
        employees_count = db.query(func.count(Employee.id)) \
            .filter(Employee.salon_id == salon.id, Employee.is_active == True, Employee.deleted_at.is_(None)) \
            .scalar() or 0
    except Exception:
        employees_count = 0

    return MobileSalonDetailResponse(
        id=str(salon.id),
        name=salon.salon_name,
        logo=logo,
        salon_images=images,
        description=description,
        address=MobileAddressInfo(name=addr_name, latitude=lat, longitude=lng, distance=dist),
        news=news,
        note=None,
        nearby_metro_station=metro,
        phone=phones,
        instagram_url=salon.salon_instagram,
        rate=rate,
        reviews_count=int(reviews_count),
        day_work_time=day_work_time,
        week_work_day=week_work_day,
        about_salon=about,
        employees_images=emp_images,
        parking=parking,
        water=water,
        coffee=coffee,
        pets=pets,
        shower=shower,
        towel=towel,
        children_service=children_service,
        onlyWomen=only_women,
        isFavorite=is_fav,
        served_users_count=served_users_count,
        employees_count=employees_count,
    )


@router.get("/", response_model=MobileSalonListResponse)
async def get_all_salons_mobile(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    """Barcha salonlarni olish (mobile)"""
    try:
        offset = (page - 1) * limit

        query = db.query(Salon).filter(Salon.is_active == True)

        if is_private != '':
            is_private_value = is_private.lower() == 'true'
            query = query.filter(Salon.private_salon == is_private_value)

        # Count total for pagination
        total = query.count()

        salons = query.order_by(Salon.created_at.desc()).offset(offset).limit(limit).all()
        items = [_build_mobile_item(s, language, db, userId) for s in salons]

        return MobileSalonListResponse(
            success=True,
            data=items,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if limit else 1,
            },
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )


@router.get("/top", response_model=List[MobileSalonItem])
async def get_top_salons_mobile(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    """Top salonlar ro'yxati (mobile)"""
    try:
        offset = (page - 1) * limit

        query = db.query(Salon).filter(
            and_(
                Salon.is_active == True,
                Salon.is_top == True
            )
        )

        if is_private != '':
            is_private_value = is_private.lower() == 'true'
            query = query.filter(Salon.private_salon == is_private_value)

        salons = query.order_by(Salon.created_at.desc()).offset(offset).limit(limit).all()
        return [_build_mobile_item(s, language, db, userId) for s in salons]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )


@router.get("/recomended", response_model=List[MobileSalonItem])
async def get_recomended_salons_mobile(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    """Tavsiya etilgan salonlar (mobile) — reyting bo'yicha"""
    try:
        offset = (page - 1) * limit

        query = db.query(Salon).filter(Salon.is_active == True)

        if is_private != '':
            is_private_value = is_private.lower() == 'true'
            query = query.filter(Salon.private_salon == is_private_value)

        salons = query.order_by(Salon.salon_rating.desc(), Salon.created_at.desc()).offset(offset).limit(limit).all()
        return [_build_mobile_item(s, language, db, userId) for s in salons]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )


@router.get("/nearby", response_model=List[MobileSalonItem])
async def get_nearby_salons_mobile(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius: float = Query(10.0, ge=0.1, le=100),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    """Yaqin atrofdagi salonlarni olish (mobile)"""
    print(f"Received coords: lat={latitude}, lng={longitude}, radius={radius}km")
    try:
        if not (-90 <= latitude <= 90):
            print("Latitude out of range")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=get_translation(language, "errors.400"))
        if not (-180 <= longitude <= 180):
            print("Longitude out of range2")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=get_translation(language, "errors.400"))

        query = db.query(Salon).filter(and_(Salon.is_active == True, Salon.location.isnot(None)))
        if is_private != '':
            is_private_value = is_private.lower() == 'true'
            query = query.filter(Salon.private_salon == is_private_value)

        all_salons = query.all()

        # Filter by distance
        nearby: List[Salon] = []
        for salon in all_salons:
            try:
                if salon.location and 'lat' in salon.location and 'lng' in salon.location:
                    salon_lat = float(salon.location['lat'])
                    salon_lng = float(salon.location['lng'])
                    distance = calculate_distance(latitude, longitude, salon_lat, salon_lng)
                    if distance <= radius:
                        nearby.append(salon)
            except Exception:
                continue


        offset = (page - 1) * limit
        salons = nearby[offset: offset + limit]
        return [_build_mobile_item(s, language, db, userId) for s in salons]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_nearby_salons_mobile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.get("/filter")
async def filter_salons_mobile(
    only_women: bool = None,
    only_female: bool = None,
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    radius: float = Query(10.0, ge=0.1, le=100),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    try:
        query = db.query(Salon).filter(and_(Salon.is_active == True, Salon.location.isnot(None)))


        
        return_values = query.all()
        # Filter by distance
        if latitude or longitude:
            if not (-90 <= latitude <= 90):
                print("Latitude out of range")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=get_translation(language, "errors.400"))
            if not (-180 <= longitude <= 180):
                print("Longitude out of range2")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=get_translation(language, "errors.400"))

            nearby: List[Salon] = []
            for salon in return_values:
                try:
                    if salon.location and 'lat' in salon.location and 'lng' in salon.location:
                        salon_lat = float(salon.location['lat'])
                        salon_lng = float(salon.location['lng'])
                        distance = calculate_distance(latitude, longitude, salon_lat, salon_lng)
                        if distance <= radius:
                            nearby.append(salon)
                except Exception:
                    continue

            offset = (page - 1) * limit
            salons = nearby[offset: offset + limit]
            nearby = [_build_mobile_item(s, language, db, userId) for s in salons]

            return_values = nearby
        if only_women or only_female:
            filtered = []
            for salon in return_values:
                comforts = salon.salon_comfort or []
                is_women = any(c["name"] == "onlyFemale" and c["isActive"] for c in comforts)
                is_female = any(c["name"] == "onlyFemale" and c["isActive"] for c in comforts)
                if (only_women and is_women) or (only_female and is_female):
                    filtered.append(salon)
            return_values = filtered
        if not return_values:
            return_values = []
        
        return return_values


    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in filter_salons_mobile: {e}, line: {e.__traceback__.tb_lineno}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )




@router.get("/{salon_id}", response_model=MobileSalonDetailResponse)
async def get_salon_by_id_mobile(
    salon_id: str,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
):
    """ID bo'yicha salonni olish (mobile)"""
    try:
        # UUID format validation
        try:
            uuid.UUID(salon_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_translation(language, "errors.400")
            )

        salon = db.query(Salon).filter(and_(Salon.id == salon_id, Salon.is_active == True)).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_translation(language, "errors.404")
            )

        return _build_mobile_detail(salon, language, db, userId, latitude, longitude)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_salon_by_id_mobile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

