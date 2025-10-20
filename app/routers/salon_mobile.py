from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, Union, List
import math
import uuid
from datetime import datetime, date, timedelta

from app.database import get_db
from app.i18nMini import get_translation
from app.models.salon import Salon
from app.models.salon_comment import SalonComment
from app.schemas.salon import (
    MobileSalonItem, 
    MobileSalonDetailResponse, 
    MobileAddressInfo, 
    MobileSalonListResponse
)
from app.models.employee import Employee, EmployeeComment
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.models.user_favourite_salon import UserFavouriteSalon
from app.models.user import User

router = APIRouter(prefix="/mobile/salons", tags=["Mobile Salons"])

# ==================== Constants ====================

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

# ==================== Pydantic Models ====================

class CommentItem(BaseModel):
    id: str
    userName: str
    userAvatar: Optional[str]
    user_id: Optional[str]
    rating: float
    comment: str
    createdAt: Optional[str]


class CommentListResponse(BaseModel):
    success: bool
    data: List[CommentItem]
    pagination: dict


# ==================== Utility Functions ====================

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula (in km)."""
    R = 6371  # Earth radius in km
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def validate_coordinates(latitude: Optional[float], longitude: Optional[float], language: str):
    """Validate latitude and longitude ranges."""
    if latitude is not None and not (-90 <= latitude <= 90):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "errors.400")
        )
    if longitude is not None and not (-180 <= longitude <= 180):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "errors.400")
        )


def get_localized_field(obj, field_prefix: str, language: Optional[str], fallback_order=["uz", "ru", "en"]) -> Optional[str]:
    """Get localized field value with fallback chain."""
    if language:
        lang = language.lower()
        if lang in fallback_order:
            val = getattr(obj, f"{field_prefix}_{lang}", None)
            if val:
                return val
    
    # Fallback chain
    for lang in fallback_order:
        val = getattr(obj, f"{field_prefix}_{lang}", None)
        if val:
            return val
    return None


def parse_is_private(is_private: Optional[str]) -> Optional[bool]:
    """Parse is_private query parameter."""
    if is_private == '':
        return None
    return is_private.lower() == 'true' if is_private else None


# ==================== Business Logic Functions ====================

def compose_news_tags(salon: Salon) -> List[str]:
    """Generate news tags for a salon (new, top, discount)."""
    tags = []
    
    try:
        # Check if salon is new (created within last 14 days)
        if salon.created_at and salon.created_at >= datetime.utcnow() - timedelta(days=14):
            tags.append("new")
        
        # Check if salon is top
        if getattr(salon, "is_top", False):
            tags.append("top")
        
        # Check for discount
        sale = salon.salon_sale
        if isinstance(sale, dict):
            percent = sale.get("percent") or sale.get("percentage")
            if isinstance(percent, (int, float)) and percent > 0:
                tags.append(f"discount-{int(percent)}%")
        elif isinstance(sale, (int, float)) and sale > 0:
            tags.append(f"discount-{int(sale)}%")
        elif isinstance(sale, str):
            import re
            match = re.search(r"(\d{1,2})", sale)
            if match:
                tags.append(f"discount-{match.group(1)}%")
    except Exception:
        pass
    
    return tags


def is_favourite_salon(db: Session, salon_id: str, user_id: Optional[str]) -> bool:
    """Check if salon is in user's favourites."""
    if not user_id:
        return False
    try:
        return db.query(UserFavouriteSalon).filter(
            UserFavouriteSalon.user_id == user_id,
            UserFavouriteSalon.salon_id == salon_id
        ).first() is not None
    except Exception:
        return False


def get_amenity_status(salon: Salon, key: str, aliases: List[str] = None) -> bool:
    """Check if a specific amenity/comfort is active."""
    aliases = aliases or []
    comforts = getattr(salon, "salon_comfort", None) or []
    
    try:
        for comfort in comforts:
            name = (comfort.get("name") or "").lower()
            is_active = bool(comfort.get("isActive"))
            if name == key.lower() or name in [a.lower() for a in aliases]:
                return is_active
    except Exception:
        pass
    return False


def get_salon_working_hours(db: Session, salon_id: str) -> Optional[str]:
    """Get today's working hours from appointments."""
    try:
        today = date.today()
        min_time = (
            db.query(func.min(Appointment.application_time))
            .join(Employee)
            .filter(Employee.salon_id == salon_id, Appointment.application_date == today)
            .scalar()
        )
        max_time = (
            db.query(func.max(Appointment.application_time))
            .join(Employee)
            .filter(Employee.salon_id == salon_id, Appointment.application_date == today)
            .scalar()
        )
        
        if min_time and max_time:
            return f"{min_time.strftime('%H:%M')} - {max_time.strftime('%H:%M')}"
    except Exception:
        pass
    return None


def get_salon_working_days(db: Session, salon_id: str) -> Optional[str]:
    """Get working days for the next week from schedules."""
    try:
        start = date.today()
        end = start + timedelta(days=6)
        
        schedule_dates = (
            db.query(Schedule.date)
            .filter(Schedule.salon_id == salon_id, Schedule.date >= start, Schedule.date <= end)
            .all()
        )
        
        weekdays = sorted({d[0].weekday() for d in schedule_dates if d and d[0]})
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        if weekdays:
            return ",".join(day_names[i] for i in weekdays)
    except Exception:
        pass
    return None


# ==================== Filter Functions ====================

def filter_by_distance(salons: List[Salon], latitude: float, longitude: float, radius: float) -> List[Salon]:
    """Filter salons within specified radius from coordinates."""
    nearby = []
    for salon in salons:
        try:
            location = salon.location
            if not location or 'lat' not in location or 'lng' not in location:
                continue
            
            distance = calculate_distance(
                latitude, longitude, 
                float(location['lat']), 
                float(location['lng'])
            )
            
            if distance <= radius:
                nearby.append(salon)
        except (ValueError, TypeError, KeyError):
            continue
    
    return nearby


def filter_by_female_only(salons: List[Salon]) -> List[Salon]:
    """Filter salons with active 'onlyFemale' or 'onlyWoman' comfort."""
    return [
        salon for salon in salons
        if any(
            c.get("name") in ["onlyFemale", "onlyWoman"] and c.get("isActive")
            for c in (salon.salon_comfort or [])
        )
    ]


def apply_types_filter(query, types: Optional[str]):
    """Apply salon types filter to SQLAlchemy query."""
    if not types:
        return query
    
    types_list = [t.strip() for t in types.split(",") if t.strip()]
    if not types_list:
        return query
    
    conditions = [
        func.JSON_CONTAINS(Salon.salon_types, f'{{"type": "{t}", "selected": true}}')
        for t in types_list
    ]
    return query.filter(or_(*conditions))


def apply_comforts_filter(query, comforts: Optional[str]):
    """Apply comforts filter to SQLAlchemy query."""
    if not comforts:
        return query
    
    comforts_list = [c.strip() for c in comforts.split(",") if c.strip()]
    if not comforts_list:
        return query
    
    conditions = [
        func.JSON_CONTAINS(Salon.salon_comfort, f'{{"name": "{c}", "isActive": true}}')
        for c in comforts_list
    ]
    return query.filter(or_(*conditions))


def apply_discount_filter(query, is_discount: Optional[bool]):
    """Apply discount filter to SQLAlchemy query."""
    if is_discount:
        return query.filter(Salon.salon_sale.has_key("discount"))
    return query


def paginate(items: List, page: int, limit: int) -> List:
    """Apply pagination to list of items."""
    offset = (page - 1) * limit
    return items[offset: offset + limit]


def build_pagination_metadata(total: int, page: int, limit: int) -> dict:
    """Build pagination metadata dictionary."""
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit if limit else 1,
    }


# ==================== Builder Functions ====================

def build_mobile_item(salon: Salon, language: Optional[str], db: Session, user_id: Optional[str]) -> MobileSalonItem:
    """Build mobile salon list item."""
    description = get_localized_field(salon, "description", language) or ""
    photos = getattr(salon, "photos", None) or []
    
    logo = photos[0] if photos else None
    salon_image = photos[1] if len(photos) > 1 else (photos[0] if photos else None)
    
    # Get city from address fields
    city = get_localized_field(salon, "address", language)
    if city:
        city = city.strip()
    
    rate = float(salon.salon_rating) if salon.salon_rating is not None else 0.0
    news = compose_news_tags(salon)
    is_fav = is_favourite_salon(db, str(salon.id), user_id)
    
    return MobileSalonItem(
        id=str(salon.id),
        name=salon.salon_name,
        description=description,
        logo=logo,
        salonImage=salon_image,
        city=city,
        rate=rate,
        reviews=0,
        news=news,
        isFavorite=is_fav,
    )


def build_mobile_detail(
    salon: Salon,
    language: Optional[str],
    db: Session,
    user_id: Optional[str],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> MobileSalonDetailResponse:
    """Build detailed mobile salon response."""
    description = get_localized_field(salon, "description", language) or ""
    photos = getattr(salon, "photos", None) or []
    logo = photos[0] if photos else None
    
    # Address
    address_name = get_localized_field(salon, "address", language)
    
    # Location and distance
    location = salon.location if isinstance(salon.location, dict) else {}
    lat = location.get("lat")
    lng = location.get("lng")
    
    distance = None
    if all([latitude, longitude, lat, lng]):
        try:
            distance = round(calculate_distance(float(latitude), float(longitude), float(lat), float(lng)), 2)
        except Exception:
            pass
    
    # Metadata
    news = compose_news_tags(salon)
    is_fav = is_favourite_salon(db, str(salon.id), user_id)
    
    # Employee images
    try:
        employees = db.query(Employee).filter(
            Employee.salon_id == str(salon.id),
            Employee.is_active == True
        ).all()
        emp_images = [e.avatar_url for e in employees if e.avatar_url]
    except Exception:
        emp_images = []
    
    # Reviews count
    try:
        reviews_count = db.query(func.count(EmployeeComment.id)).join(Employee).filter(
            Employee.salon_id == str(salon.id)
        ).scalar() or 0
    except Exception:
        reviews_count = 0
    
    # Working hours and days
    day_work_time = get_salon_working_hours(db, str(salon.id))
    week_work_day = get_salon_working_days(db, str(salon.id))
    
    # Amenities
    amenities = {
        "parking": get_amenity_status(salon, "parking"),
        "water": get_amenity_status(salon, "water"),
        "coffee": get_amenity_status(salon, "coffee", ["cafee"]),
        "pets": get_amenity_status(salon, "pets"),
        "shower": get_amenity_status(salon, "shower", ["bath"]),
        "towel": get_amenity_status(salon, "towel"),
        "children_service": get_amenity_status(salon, "children_service", ["kids"]),
        "only_women": get_amenity_status(salon, "onlyWomen", ["onlyFemale"]),
    }
    
    # Nearby metro
    metro = get_localized_field(salon, "orientation", language)
    
    # Phone numbers
    phones = [salon.salon_phone] if salon.salon_phone else []
    
    # Rating
    rate = float(salon.salon_rating) if salon.salon_rating is not None else 0.0
    
    # Statistics
    try:
        served_users_count = db.query(func.count(Appointment.id)).join(Employee).filter(
            Employee.salon_id == salon.id,
            Appointment.status == 'done'
        ).scalar() or 0
    except Exception:
        served_users_count = 0
    
    try:
        employees_count = db.query(func.count(Employee.id)).filter(
            Employee.salon_id == salon.id,
            Employee.is_active == True,
            Employee.deleted_at.is_(None)
        ).scalar() or 0
    except Exception:
        employees_count = 0
    
    return MobileSalonDetailResponse(
        id=str(salon.id),
        name=salon.salon_name,
        logo=logo,
        salon_images=photos,
        description=description,
        address=MobileAddressInfo(name=address_name, latitude=lat, longitude=lng, distance=distance),
        news=news,
        note=None,
        nearby_metro_station=metro,
        phone=phones,
        instagram_url=salon.salon_instagram,
        rate=rate,
        reviews_count=int(reviews_count),
        day_work_time=day_work_time,
        week_work_day=week_work_day,
        about_salon=description,
        employees_images=emp_images,
        parking=amenities["parking"],
        water=amenities["water"],
        coffee=amenities["coffee"],
        pets=amenities["pets"],
        shower=amenities["shower"],
        towel=amenities["towel"],
        children_service=amenities["children_service"],
        onlyWomen=amenities["only_women"],
        isFavorite=is_fav,
        served_users_count=served_users_count,
        employees_count=employees_count,
    )


# ==================== API Endpoints ====================

@router.get("/", response_model=MobileSalonListResponse)
async def get_all_salons(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db),
    language: Optional[str] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    """Get all active salons with pagination."""
    try:
        query = db.query(Salon).filter(Salon.is_active == True)
        
        # Apply private filter
        private_value = parse_is_private(is_private)
        if private_value is not None:
            query = query.filter(Salon.private_salon == private_value)
        
        total = query.count()
        offset = (page - 1) * limit
        salons = query.order_by(Salon.created_at.desc()).offset(offset).limit(limit).all()
        
        items = [build_mobile_item(s, language, db, userId) for s in salons]
        
        return MobileSalonListResponse(
            success=True,
            data=items,
            pagination=build_pagination_metadata(total, page, limit),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )


# @router.get("/top", response_model=List[MobileSalonItem])
# async def get_top_salons(
#     page: int = Query(1, ge=1),
#     limit: int = Query(10, ge=1, le=100),
#     is_private: Optional[str] = Query(''),
#     db: Session = Depends(get_db),
#     language: Optional[str] = Header(None, alias="X-User-language"),
#     userId: Optional[str] = Query(None),
# ):
#     """Get top-rated salons."""
#     try:
#         query = db.query(Salon).filter(Salon.is_active == True, Salon.is_top == True)
        
#         private_value = parse_is_private(is_private)
#         if private_value is not None:
#             query = query.filter(Salon.private_salon == private_value)
        
#         offset = (page - 1) * limit
#         salons = query.order_by(Salon.created_at.desc()).offset(offset).limit(limit).all()
        
#         return [build_mobile_item(s, language, db, userId) for s in salons]
#     except Exception:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=get_translation(language, "errors.500")
#         )


# @router.get("/recomended", response_model=List[MobileSalonItem])
# async def get_recommended_salons(
#     page: int = Query(1, ge=1),
#     limit: int = Query(10, ge=1, le=100),
#     is_private: Optional[str] = Query(''),
#     db: Session = Depends(get_db),
#     language: Optional[str] = Header(None, alias="X-User-language"),
#     userId: Optional[str] = Query(None),
# ):
#     """Get recommended salons sorted by rating."""
#     try:
#         query = db.query(Salon).filter(Salon.is_active == True)
        
#         private_value = parse_is_private(is_private)
#         if private_value is not None:
#             query = query.filter(Salon.private_salon == private_value)
        
#         offset = (page - 1) * limit
#         salons = query.order_by(
#             Salon.salon_rating.desc(), 
#             Salon.created_at.desc()
#         ).offset(offset).limit(limit).all()
        
#         return [build_mobile_item(s, language, db, userId) for s in salons]
#     except Exception:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=get_translation(language, "errors.500")
#         )




@router.get("/filter")
async def filter_salons(
    isTop: Optional[bool] = None,
    isRecommended: Optional[bool] = None,
    only_women: Optional[bool] = None,
    only_female: Optional[bool] = None,
    isAir: Optional[bool] = Query(None),
    forChildren: Optional[bool] = Query(None),
    isDiscount: Optional[bool] = None,
    types: Optional[str] = Query(None, description="Comma-separated salon types"),
    comforts: Optional[str] = Query(None, description="Comma-separated comforts"),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    radius: float = Query(10.0, ge=0.1, le=100),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    language: Optional[str] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    """Filter salons by multiple criteria."""
    try:
        if latitude is not None or longitude is not None:
            validate_coordinates(latitude, longitude, language)
        
        # Build base query with database-level filters
        query = db.query(Salon).filter(Salon.is_active == True, Salon.location.isnot(None))
        if isTop:
            query = query.filter(Salon.is_top == True)
        is_recommended = isRecommended if isRecommended is not None else True
        if is_recommended:
            query = query.order_by(Salon.salon_rating.desc(), Salon.created_at.desc())

        # Extend types with isAir/forChildren flags
        existing_types_list = [t.strip() for t in types.split(",") if t.strip()] if types else []
        if isAir:
            existing_types_list.append("hair_services")
        if forChildren:
            existing_types_list.append("for_children")
        effective_types = ",".join(existing_types_list) if existing_types_list else None

        query = apply_types_filter(query, effective_types)
        query = apply_comforts_filter(query, comforts)
        query = apply_discount_filter(query, isDiscount)
        
        # Paginate
        total = query.count()
        offset = (page - 1) * limit
        salons = query.offset(offset).limit(limit).all()
        
        # Apply in-memory filters
        if only_women or only_female:
            salons = filter_by_female_only(salons)
        
        if latitude is not None and longitude is not None:
            salons = filter_by_distance(salons, latitude, longitude, radius)
        
        # Build response
        return {
            "success": True,
            "data": [build_mobile_item(s, language, db, userId) for s in salons],
            "pagination": build_pagination_metadata(total, page, limit),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in filter_salons: {e}, line: {e.__traceback__.tb_lineno}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.get("/nearby", response_model=List[MobileSalonItem])
async def get_nearby_salons(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius: float = Query(10.0, ge=0.1, le=100),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db),
    language: Optional[str] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    """Get nearby salons within specified radius."""
    try:
        validate_coordinates(latitude, longitude, language)
        
        query = db.query(Salon).filter(Salon.is_active == True, Salon.location.isnot(None))
        
        private_value = parse_is_private(is_private)
        if private_value is not None:
            query = query.filter(Salon.private_salon == private_value)
        
        all_salons = query.all()
        nearby = filter_by_distance(all_salons, latitude, longitude, radius)
        paginated = paginate(nearby, page, limit)
        
        return [build_mobile_item(s, language, db, userId) for s in paginated]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_nearby_salons: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )


@router.get("/comments/{salon_id}", response_model=CommentListResponse)
async def get_salon_comments(
    salon_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    language: Optional[str] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    """Get comments for a specific salon."""
    salon = db.query(Salon).filter(Salon.id == salon_id, Salon.is_active == True).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404")
        )
    
    offset = (page - 1) * limit
    comments_query = db.query(SalonComment).filter(SalonComment.salon_id == salon_id)
    total = comments_query.count()
    comments = comments_query.order_by(SalonComment.created_at.desc()).offset(offset).limit(limit).all()
    
    items = []
    for comment in comments:
        user = db.query(User).filter(User.id == comment.user_id).first()
        if not user:
            continue
        
        items.append(CommentItem(
            id=str(comment.id),
            userName=user.full_name or "Anonymous",
            userAvatar=user.avatar_url,
            user_id=str(comment.user_id),
            rating=float(comment.rating) if comment.rating and str(comment.rating).isdigit() else 0.0,
            comment=comment.text or "",
            createdAt=str(comment.created_at) if comment.created_at else None,
        ))
    
    return CommentListResponse(
        success=True,
        data=items,
        pagination={"page": page, "limit": limit, "total": total}
    )


@router.get("/{salon_id}", response_model=MobileSalonDetailResponse)
async def get_salon_by_id(
    salon_id: str,
    db: Session = Depends(get_db),
    language: Optional[str] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
):
    """Get detailed salon information by ID."""
    try:
        # Validate UUID format
        try:
            uuid.UUID(salon_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_translation(language, "errors.400")
            )
        
        salon = db.query(Salon).filter(Salon.id == salon_id, Salon.is_active == True).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_translation(language, "errors.404")
            )
        
        return build_mobile_detail(salon, language, db, userId, latitude, longitude)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_salon_by_id: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )