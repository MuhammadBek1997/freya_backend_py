from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, Union, List
import math
import uuid

from app.database import get_db
from app.i18nMini import get_translation
from app.models.salon import Salon
from app.schemas.salon import MobileSalonItem
from app.models.user_favourite_salon import UserFavouriteSalon

router = APIRouter(prefix="/mobile/salons", tags=["Mobile Salons"])

# Default values
DEFAULT_SALON_TYPES = [
    {"type": "Beauty Salon", "selected": True},
    {"type": "Fitness", "selected": False},
    {"type": "Functional Training", "selected": False},
    {"type": "Yoga", "selected": False},
    {"type": "Massage", "selected": False}
]

DEFAULT_LOCATION = {"lat": 41, "lng": 64}

DEFAULT_SALON_COMFORT = [
    {"name": "parking", "isActive": False},
    {"name": "cafee", "isActive": False},
    {"name": "onlyFemale", "isActive": False},
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


@router.get("/", response_model=List[MobileSalonItem])
async def get_all_salons_mobile(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    isTop: Optional[bool] = None,
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    """Barcha salonlarni olish (mobile)"""
    try:
        offset = (page - 1) * limit

        query = db.query(Salon).filter(Salon.is_active == True)

        if search:
            query = query.filter(
                or_(
                    Salon.salon_name.ilike(f"%{search}%"),
                    Salon.salon_description.ilike(f"%{search}%")
                )
            )

        if isTop is not None:
            query = query.filter(Salon.is_top == isTop)

        if is_private != '':
            is_private_value = is_private.lower() == 'true'
            query = query.filter(Salon.private_salon == is_private_value)

        salons = query.order_by(Salon.created_at.desc()).offset(offset).limit(limit).all()
        return [_build_mobile_item(s, language, db, userId) for s in salons]
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

@router.get("/{salon_id}", response_model=MobileSalonItem)
async def get_salon_by_id_mobile(
    salon_id: str,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
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

        return _build_mobile_item(salon, language, db, userId)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

