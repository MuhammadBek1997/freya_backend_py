from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from typing import List, Optional, Union
import math
import json
from decimal import Decimal
from datetime import datetime
import uuid

from app.database import get_db
from app.i18nMini import get_translation
from app.models.salon import Salon
from app.models.user import User
from app.models.employee import Employee
from app.models.appointment import Appointment
from app.schemas.salon import (
    SalonCreate, SalonUpdate, SalonResponse, SalonListResponse,
    SalonCommentCreate, SalonCommentResponse, NearbySalonsRequest,
    SalonTypesFilterRequest, PhotoUploadRequest, PhotoDeleteRequest,
    StandardResponse, ErrorResponse
)
from app.auth.jwt_utils import JWTUtils
from app.middleware.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/salons", tags=["Salons"])

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
    {"name": "water", "isActive": False},
    {"name": "pets", "isActive": False},
    {"name": "bath", "isActive": False},
    {"name": "towel", "isActive": False},
    {"name": "kids", "isActive": False}
]

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

@router.post("/", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def create_salon(
    salon_data: SalonCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Yangi salon yaratish"""
    try:
        # Get salon data
        salon_name = salon_data.salon_name
        salon_phone = salon_data.salon_phone
        
        if not salon_name or salon_name.strip() == '':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_translation(language, "errors.400")
            )
        
        # Set default values (also when provided lists are empty)
        salon_types = (
            salon_data.salon_types if (salon_data.salon_types and len(salon_data.salon_types) > 0) else DEFAULT_SALON_TYPES
        )
        # Location: handle cases where Location object is provided but empty
        if salon_data.location and hasattr(salon_data.location, 'dict'):
            loc_dict = salon_data.location.dict()
            lat_val = loc_dict.get('latitude')
            lng_val = loc_dict.get('longitude')
            if lat_val is None or lng_val is None:
                location_dict = DEFAULT_LOCATION
            else:
                # Normalize keys to {lat, lng}
                location_dict = {"lat": lat_val, "lng": lng_val}
        else:
            location_dict = DEFAULT_LOCATION
        salon_comfort = (
            salon_data.salon_comfort if (salon_data.salon_comfort and len(salon_data.salon_comfort) > 0) else DEFAULT_SALON_COMFORT
        )
        
        # Convert Pydantic models to dict for JSON storage
        salon_types_dict = [st.dict() if hasattr(st, 'dict') else st for st in salon_types]
        salon_comfort_dict = [sc.dict() if hasattr(sc, 'dict') else sc for sc in salon_comfort]
        
        # Create new salon
        new_salon = Salon(
            salon_name=salon_name,
            salon_phone=salon_phone,
            salon_instagram=salon_data.salon_instagram,
            salon_rating=salon_data.salon_rating or Decimal('0'),
            salon_types=salon_types_dict,
            private_salon=salon_data.private_salon or False,
            location=location_dict,
            salon_comfort=salon_comfort_dict,
            salon_sale=salon_data.salon_sale,
            logo=salon_data.logo,
            is_active=True,
            is_private=salon_data.is_private or False,

            description_uz=salon_data.description_uz,
            description_ru=salon_data.description_ru,
            description_en=salon_data.description_en,
            address_uz=salon_data.address_uz,
            address_ru=salon_data.address_ru,
            address_en=salon_data.address_en,
            orientation_uz=salon_data.orientation_uz,
            orientation_ru=salon_data.orientation_ru,
            orientation_en=salon_data.orientation_en,
        )
        
        db.add(new_salon)
        db.commit()
        db.refresh(new_salon)
        
        return StandardResponse(
            success=True,
            message=get_translation(language, "success"),
            data={
                "id": str(new_salon.id),
                "salon_name": new_salon.salon_name,
                "salon_phone": new_salon.salon_phone,
                "logo": new_salon.logo,
                "is_active": new_salon.is_active,
                "created_at": new_salon.created_at.isoformat() if new_salon.created_at else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.get("/", response_model=SalonListResponse)
async def get_all_salons(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    isTop: bool = None,
    isDiscount: bool = None,
    search: Optional[str] = Query(None),
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Barcha salonlarni olish"""
    try:
        offset = (page - 1) * limit
        
        # Base query
        query = db.query(Salon).filter(Salon.is_active == True)
        
        # Search filter
        if search:
            search_filter = or_(
                Salon.salon_name.ilike(f"%{search}%"),
                Salon.salon_description.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        # Top salon filter
        # If isTop is true, filter salons that have is_top set to true
        # If isTop is false, filter salons that have is_top set to false
        if isTop is not None:
            query = query.filter(Salon.is_top == isTop)
        
        # Discount salon filter
        # If isDiscount is true, filter salons that have a discount
        # If isDiscount is false, filter salons that do not have a discount
        if isDiscount is not None:
            if isDiscount:
                query = query.where(Salon.salon_sale.has_key('discount'))
        # Private salon filter
        if is_private != '':
            is_private_value = is_private.lower() == 'true'
            query = query.filter(Salon.private_salon == is_private_value)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        salons = query.order_by(Salon.created_at.desc()).offset(offset).limit(limit).all()
        
        total_pages = math.ceil(total / limit)
        
        # Convert salons to SalonResponse objects with proper UUID handling
        salon_responses = []
        for salon in salons:
            # Fallback to defaults when fields are empty
            st = salon.salon_types if (salon.salon_types and len(salon.salon_types) > 0) else DEFAULT_SALON_TYPES
            sc = salon.salon_comfort if (salon.salon_comfort and len(salon.salon_comfort) > 0) else DEFAULT_SALON_COMFORT
            loc = salon.location or DEFAULT_LOCATION

            salon_dict = {
                "id": str(salon.id),
                "salon_name": salon.salon_name,
                "salon_phone": salon.salon_phone,
                "salon_instagram": salon.salon_instagram,
                "salon_rating": salon.salon_rating,
                "salon_types": st,
                "private_salon": salon.private_salon,
                "location": loc,
                "salon_comfort": sc,
                "salon_sale": salon.salon_sale,
                "is_active": salon.is_active,
                "is_private": salon.is_private,
                "photos": salon.photos,
                "logo": salon.logo,
                "description_uz": salon.description_uz,
                "description_ru": salon.description_ru,
                "description_en": salon.description_en,
                "address_uz": salon.address_uz,
                "address_ru": salon.address_ru,
                "address_en": salon.address_en,
                # Qo'shimcha maydonlar: xizmat ko'rsatilgan odamlar va xodimlar soni
                "served_users_count": db.query(func.count(Appointment.id))
                .join(Employee, Appointment.employee_id == Employee.id)
                .filter(Employee.salon_id == salon.id, Appointment.status == 'done')
                .scalar() or 0,
                "employees_count": db.query(func.count(Employee.id))
                .filter(Employee.salon_id == salon.id, Employee.is_active == True, Employee.deleted_at.is_(None))
                .scalar() or 0,
                "created_at": salon.created_at,
                "updated_at": salon.updated_at
            }
            salon_responses.append(SalonResponse(**salon_dict))

        return SalonListResponse(
            salons=salon_responses,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.get("/{salon_id}", response_model=SalonResponse)
async def get_salon_by_id(
    salon_id: str,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """ID bo'yicha salonni olish"""
    try:
        # UUID format validation
        try:
            uuid.UUID(salon_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_translation(language, "errors.400")
            )
        
        salon = db.query(Salon).filter(
            and_(Salon.id == salon_id, Salon.is_active == True)
        ).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_translation(language, "errors.404")
            )
        
        # Convert salon to SalonResponse with proper UUID handling
        st = salon.salon_types if (salon.salon_types and len(salon.salon_types) > 0) else DEFAULT_SALON_TYPES
        sc = salon.salon_comfort if (salon.salon_comfort and len(salon.salon_comfort) > 0) else DEFAULT_SALON_COMFORT
        loc = salon.location or DEFAULT_LOCATION
        salon_dict = {
            "id": str(salon.id),
            "salon_name": salon.salon_name,
            "salon_phone": salon.salon_phone,
            "salon_instagram": salon.salon_instagram,
            "salon_rating": salon.salon_rating,
            "salon_description": salon.description_uz,  # Use description_uz as default
            "salon_types": st,
            "private_salon": salon.private_salon,
            "location": loc,
            "salon_comfort": sc,
            "salon_sale": salon.salon_sale,
            "is_active": salon.is_active,
            "is_private": salon.is_private,
            "photos": salon.photos,
            "logo": salon.logo,
            "description_uz": salon.description_uz,
            "description_ru": salon.description_ru,
            "description_en": salon.description_en,
            "address_uz": salon.address_uz,
            "address_ru": salon.address_ru,
            "address_en": salon.address_en,
            # Qo'shimcha maydonlar: xizmat ko'rsatilgan odamlar va xodimlar soni
            "served_users_count": db.query(func.count(Appointment.id))
            .join(Employee, Appointment.employee_id == Employee.id)
            .filter(Employee.salon_id == salon.id, Appointment.status == 'done')
            .scalar() or 0,
            "employees_count": db.query(func.count(Employee.id))
            .filter(Employee.salon_id == salon.id, Employee.is_active == True, Employee.deleted_at.is_(None))
            .scalar() or 0,
            "created_at": salon.created_at,
            "updated_at": salon.updated_at
        }
        return SalonResponse(**salon_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.put("/{salon_id}", response_model=StandardResponse)
async def update_salon(
    salon_id: str,
    salon_data: SalonUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Salonni yangilash"""
    try:
        salon = db.query(Salon).where(Salon.id == salon_id).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_translation(language, "errors.404")
            )
        
        # Update fields
        update_data = salon_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(salon, field):
                # Convert Pydantic models to dict for JSON fields and apply defaults on empty
                if field in ['salon_types', 'salon_comfort']:
                    if value is None or (isinstance(value, list) and len(value) == 0):
                        value = DEFAULT_SALON_TYPES if field == 'salon_types' else DEFAULT_SALON_COMFORT
                    else:
                        value = [item.dict() if hasattr(item, 'dict') else item for item in value]
                elif field == 'location':
                    # Normalize and apply defaults when Location is empty or partial
                    if value is None:
                        value = DEFAULT_LOCATION
                    elif hasattr(value, 'dict'):
                        loc_dict = value.dict()
                        lat_val = loc_dict.get('latitude')
                        lng_val = loc_dict.get('longitude')
                        if lat_val is None or lng_val is None:
                            value = DEFAULT_LOCATION
                        else:
                            value = {"lat": lat_val, "lng": lng_val}
                    elif isinstance(value, dict):
                        # If dict is provided, try to standardize keys
                        if 'lat' in value and 'lng' in value:
                            value = {"lat": value['lat'], "lng": value['lng']}
                        elif 'latitude' in value and 'longitude' in value:
                            value = {"lat": value['latitude'], "lng": value['longitude']}
                        else:
                            value = DEFAULT_LOCATION
                
                setattr(salon, field, value)
        
        db.commit()
        db.refresh(salon)
        
        return StandardResponse(
            success=True,
            message=get_translation(language, "success"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.delete("/{salon_id}", response_model=StandardResponse)
async def delete_salon(
    salon_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Salonni o'chirish (soft delete)"""
    try:
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_translation(language, "errors.404")
            )
        
        salon.is_active = False
        db.commit()
        
        return StandardResponse(
            success=True,
            message=get_translation(language, "success"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.post("/apply-defaults", response_model=StandardResponse)
async def apply_defaults_to_salons(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Bo'sh salon_types va salon_comfort uchun defaultlarni DBga qo'llash"""
    try:
        salons = db.query(Salon).filter(Salon.is_active == True).all()
        updated_count = 0
        for salon in salons:
            changed = False
            if not salon.salon_types or (isinstance(salon.salon_types, list) and len(salon.salon_types) == 0):
                salon.salon_types = DEFAULT_SALON_TYPES
                changed = True
            if not salon.salon_comfort or (isinstance(salon.salon_comfort, list) and len(salon.salon_comfort) == 0):
                salon.salon_comfort = DEFAULT_SALON_COMFORT
                changed = True
            if changed:
                updated_count += 1
        db.commit()
        return StandardResponse(
            success=True,
            message=get_translation(language, "success"),
            data={"updated_count": updated_count}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.post("/{salon_id}/comments", response_model=StandardResponse)
async def add_salon_comment(
    salon_id: str,
    comment_data: SalonCommentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Salon uchun izoh qo'shish"""
    try:
        salon = db.query(Salon).filter(
            and_(Salon.id == salon_id, Salon.is_active == True)
        ).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_translation(language, "errors.404")
            )
        
        # Add comment to salon's comments JSON field
        new_comment = {
            "user_id": str(current_user.id),
            "text": comment_data.text,
            "rating": comment_data.rating,
            "created_at": str(datetime.utcnow())
        }
        
        current_comments = salon.comments or []
        current_comments.append(new_comment)
        salon.comments = current_comments
        
        # Update salon rating
        total_rating = sum(comment.get('rating', 0) for comment in current_comments)
        salon.salon_rating = Decimal(str(total_rating / len(current_comments)))
        
        db.commit()
        
        return StandardResponse(
            success=True,
            message=get_translation(language, "success"),
            data=new_comment
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.get("/nearby", response_model=SalonListResponse)
async def get_nearby_salons(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius: float = Query(10.0, ge=0.1, le=100),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Yaqin atrofdagi salonlarni olish"""
    print(f"Received coords: lat={latitude}, lng={longitude}, radius={radius}km1")
    try:
        # Validate coordinates
        if not -90 <= latitude <= 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_translation(language, "errors.400")
            )
        
        if not -180 <= longitude <= 180:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_translation(language, "errors.400")
            )
        
        # Get all active salons with location data
        query = db.query(Salon).filter(
            and_(
                Salon.is_active == True,
                Salon.location.isnot(None)
            )
        )
        
        # Private salon filter
        if is_private != '':
            is_private_value = is_private.lower() == 'true'
            query = query.filter(Salon.private_salon == is_private_value)
        
        all_salons = query.all()
        
        # Filter salons by distance
        nearby_salons = []
        for salon in all_salons:
            if salon.location and 'lat' in salon.location and 'lng' in salon.location:
                salon_lat = float(salon.location['lat'])
                salon_lng = float(salon.location['lng'])
                
                distance = calculate_distance(latitude, longitude, salon_lat, salon_lng)
                
                if distance <= radius:
                    # Add distance to salon object
                    salon_dict = salon.__dict__.copy()
                    salon_dict['distance'] = round(distance, 2)
                    # Qo'shimcha maydonlar: xizmat ko'rsatilgan odamlar va xodimlar soni
                    salon_dict['served_users_count'] = db.query(func.count(Appointment.id)) \
                        .join(Employee, Appointment.employee_id == Employee.id) \
                        .filter(Employee.salon_id == salon.id, Appointment.status == 'done') \
                        .scalar() or 0
                    salon_dict['employees_count'] = db.query(func.count(Employee.id)) \
                        .filter(Employee.salon_id == salon.id, Employee.is_active == True, Employee.deleted_at.is_(None)) \
                        .scalar() or 0
                    nearby_salons.append(salon_dict)
        
        # Sort by distance
        nearby_salons.sort(key=lambda x: x['distance'])
        
        # Pagination
        total = len(nearby_salons)
        offset = (page - 1) * limit
        paginated_salons = nearby_salons[offset:offset + limit]
        
        total_pages = math.ceil(total / limit)
        
        return SalonListResponse(
            salons=paginated_salons,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.get("/filter/types", response_model=SalonListResponse)
async def get_salons_by_types(
    types: Optional[str] = Query(None, description="Comma-separated salon types"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(''),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Salon turlari bo'yicha filtrlash"""
    try:
        # Parse salon_types (comma-separated string)
        types_to_filter = [t.strip() for t in types.split(',')]
        
        if not types_to_filter:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_translation(language, "errors.400")
            )
        
        # Base query
        query = db.query(Salon).filter(Salon.is_active == True)
        
        # Search filter
        if search:
            search_filter = or_(
                Salon.salon_name.ilike(f"%{search}%"),
                Salon.salon_description.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Filter by salon types using JSON operations
        type_conditions = []
        for salon_type in types_to_filter:
            type_conditions.append(
                func.JSON_CONTAINS(
                    Salon.salon_types,
                    f'{{"type": "{salon_type}", "selected": true}}'
                )
            )

        if type_conditions:
            query = query.filter(or_(*type_conditions))
        
        # Get total count
        total = query.count()
        
        # Pagination
        offset = (page - 1) * limit
        salons = query.order_by(Salon.salon_rating.desc(), Salon.salon_name.asc()).offset(offset).limit(limit).all()
        
        total_pages = math.ceil(total / limit)
        
        # Map and enrich salons with counts
        salon_responses: List[SalonResponse] = []
        for salon in salons:
            st = salon.salon_types if (salon.salon_types and len(salon.salon_types) > 0) else DEFAULT_SALON_TYPES
            sc = salon.salon_comfort if (salon.salon_comfort and len(salon.salon_comfort) > 0) else DEFAULT_SALON_COMFORT
            loc = salon.location or DEFAULT_LOCATION
            salon_dict = {
                "id": str(salon.id),
                "salon_name": salon.salon_name,
                "salon_phone": salon.salon_phone,
                "salon_instagram": salon.salon_instagram,
                "salon_rating": salon.salon_rating,
                "salon_types": st,
                "private_salon": salon.private_salon,
                "location": loc,
                "salon_comfort": sc,
                "salon_sale": salon.salon_sale,
                "is_active": salon.is_active,
                "is_private": salon.is_private,
                "photos": salon.photos,
                "logo": salon.logo,
                "description_uz": salon.description_uz,
                "description_ru": salon.description_ru,
                "description_en": salon.description_en,
                "address_uz": salon.address_uz,
                "address_ru": salon.address_ru,
                "address_en": salon.address_en,
                # Qo'shimcha maydonlar: xizmat ko'rsatilgan odamlar va xodimlar soni
                "served_users_count": db.query(func.count(Appointment.id))
                .join(Employee, Appointment.employee_id == Employee.id)
                .filter(Employee.salon_id == salon.id, Appointment.status == 'done')
                .scalar() or 0,
                "employees_count": db.query(func.count(Employee.id))
                .filter(Employee.salon_id == salon.id, Employee.is_active == True, Employee.deleted_at.is_(None))
                .scalar() or 0,
                "created_at": salon.created_at,
                "updated_at": salon.updated_at
            }
            salon_responses.append(SalonResponse(**salon_dict))

        return SalonListResponse(
            salons=salon_responses,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}, line: {e.__traceback__.tb_lineno}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.post("/{salon_id}/photos", response_model=StandardResponse)
async def upload_salon_photos(
    salon_id: str,
    photo_data: PhotoUploadRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Salon rasmlari yuklash"""
    try:
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_translation(language, "errors.404")
            )
        
        current_photos = salon.photos or []
        updated_photos = current_photos + photo_data.photos
        
        salon.photos = updated_photos
        db.commit()
        
        return StandardResponse(
            success=True,
            message=get_translation(language, "success"),
            data={
                "salon_id": salon_id,
                "photos": updated_photos,
                "total_photos": len(updated_photos)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.delete("/{salon_id}/photos", response_model=StandardResponse)
async def delete_salon_photo(
    salon_id: str,
    photo_data: PhotoDeleteRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Salon rasmini o'chirish"""
    try:
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_translation(language, "errors.404")
            )
        
        current_photos = salon.photos or []
        
        if photo_data.photo_index >= len(current_photos):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_translation(language, "errors.400")
            )
        
        # Remove photo at specified index
        updated_photos = current_photos[:photo_data.photo_index] + current_photos[photo_data.photo_index + 1:]
        
        salon.photos = updated_photos
        db.commit()
        
        return StandardResponse(
            success=True,
            message=get_translation(language, "success"),
            data={
                "salon_id": salon_id,
                "photos": updated_photos,
                "deleted_photo_index": photo_data.photo_index,
                "remaining_photos_count": len(updated_photos)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )