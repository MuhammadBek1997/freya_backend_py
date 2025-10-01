from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from typing import List, Optional
import math
import json
from decimal import Decimal
from datetime import datetime

from app.database import get_db
from app.models.salon import Salon
from app.models.user import User
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
    {"name": "kids", "isActive": True}
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
    current_user = Depends(get_current_admin)
):
    """Yangi salon yaratish"""
    try:
        # Use salon_name if provided, otherwise fallback to name
        salon_name = salon_data.salon_name or salon_data.name
        salon_phone = salon_data.salon_phone or salon_data.phone
        salon_description = salon_data.salon_description or salon_data.description
        
        if not salon_name or salon_name.strip() == '':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Salon nomi (salon_name) majburiy"
            )
        
        # Set default values
        salon_types = salon_data.salon_types or DEFAULT_SALON_TYPES
        location = salon_data.location or DEFAULT_LOCATION
        salon_orient = salon_data.salon_orient or DEFAULT_LOCATION
        salon_comfort = salon_data.salon_comfort or DEFAULT_SALON_COMFORT
        
        # Convert Pydantic models to dict for JSON storage
        salon_types_dict = [st.dict() if hasattr(st, 'dict') else st for st in salon_types]
        location_dict = location.dict() if hasattr(location, 'dict') else location
        salon_orient_dict = salon_orient.dict() if hasattr(salon_orient, 'dict') else salon_orient
        salon_comfort_dict = [sc.dict() if hasattr(sc, 'dict') else sc for sc in salon_comfort]
        
        # Create new salon
        new_salon = Salon(
            salon_name=salon_name,
            salon_phone=salon_phone,
            salon_add_phone=salon_data.salon_add_phone,
            salon_instagram=salon_data.salon_instagram,
            salon_rating=salon_data.salon_rating or Decimal('0'),
            comments=salon_data.comments or [],
            salon_payment=salon_data.salon_payment or {},
            salon_description=salon_description,
            salon_types=salon_types_dict,
            private_salon=salon_data.private_salon or False,
            work_schedule=salon_data.work_schedule or [],
            salon_title=salon_data.salon_title,
            salon_additionals=salon_data.salon_additionals or [],
            sale_percent=salon_data.sale_percent or 0,
            sale_limit=salon_data.sale_limit or 0,
            location=location_dict,
            salon_orient=salon_orient_dict,
            salon_photos=salon_data.salon_photos or [],
            salon_comfort=salon_comfort_dict,
            is_active=True
        )
        
        db.add(new_salon)
        db.commit()
        db.refresh(new_salon)
        
        return StandardResponse(
            success=True,
            message="Salon muvaffaqiyatli yaratildi",
            data=new_salon
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server xatoligi: {str(e)}"
        )

@router.get("/", response_model=SalonListResponse)
async def get_all_salons(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db)
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
        
        # Private salon filter
        if is_private != '':
            is_private_value = is_private.lower() == 'true'
            query = query.filter(Salon.private_salon == is_private_value)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        salons = query.order_by(Salon.created_at.desc()).offset(offset).limit(limit).all()
        
        total_pages = math.ceil(total / limit)
        
        return SalonListResponse(
            salons=salons,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server xatoligi: {str(e)}"
        )

@router.get("/{salon_id}", response_model=SalonResponse)
async def get_salon_by_id(
    salon_id: str,
    db: Session = Depends(get_db)
):
    """ID bo'yicha salonni olish"""
    try:
        salon = db.query(Salon).filter(
            and_(Salon.id == salon_id, Salon.is_active == True)
        ).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon topilmadi"
            )
        
        return salon
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server xatoligi: {str(e)}"
        )

@router.put("/{salon_id}", response_model=StandardResponse)
async def update_salon(
    salon_id: str,
    salon_data: SalonUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Salonni yangilash"""
    try:
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon topilmadi"
            )
        
        # Update fields
        update_data = salon_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(salon, field):
                # Convert Pydantic models to dict for JSON fields
                if field in ['salon_types', 'salon_comfort'] and value:
                    value = [item.dict() if hasattr(item, 'dict') else item for item in value]
                elif field in ['location', 'salon_orient'] and value:
                    value = value.dict() if hasattr(value, 'dict') else value
                
                setattr(salon, field, value)
        
        db.commit()
        db.refresh(salon)
        
        return StandardResponse(
            success=True,
            message="Salon muvaffaqiyatli yangilandi",
            data=salon
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server xatoligi: {str(e)}"
        )

@router.delete("/{salon_id}", response_model=StandardResponse)
async def delete_salon(
    salon_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Salonni o'chirish (soft delete)"""
    try:
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon topilmadi"
            )
        
        salon.is_active = False
        db.commit()
        
        return StandardResponse(
            success=True,
            message="Salon muvaffaqiyatli o'chirildi"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server xatoligi: {str(e)}"
        )

@router.post("/{salon_id}/comments", response_model=StandardResponse)
async def add_salon_comment(
    salon_id: str,
    comment_data: SalonCommentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Salon uchun izoh qo'shish"""
    try:
        salon = db.query(Salon).filter(
            and_(Salon.id == salon_id, Salon.is_active == True)
        ).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon topilmadi"
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
            message="Izoh muvaffaqiyatli qo'shildi",
            data=new_comment
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server xatoligi: {str(e)}"
        )

@router.get("/nearby", response_model=SalonListResponse)
async def get_nearby_salons(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius: float = Query(10.0, ge=0.1, le=100),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db)
):
    """Yaqin atrofdagi salonlarni olish"""
    try:
        # Validate coordinates
        if not -90 <= latitude <= 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Noto'g'ri latitude qiymati"
            )
        
        if not -180 <= longitude <= 180:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Noto'g'ri longitude qiymati"
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
            detail=f"Server xatoligi: {str(e)}"
        )

@router.get("/filter/types", response_model=SalonListResponse)
async def get_salons_by_types(
    salon_types: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(''),
    db: Session = Depends(get_db)
):
    """Salon turlari bo'yicha filtrlash"""
    try:
        # Parse salon_types (comma-separated string)
        types_to_filter = [t.strip() for t in salon_types.split(',')]
        
        if not types_to_filter:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="salon_types parametri majburiy"
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
                Salon.salon_types.op('@>')([{"type": salon_type}])
            )
        
        if type_conditions:
            query = query.filter(or_(*type_conditions))
        
        # Get total count
        total = query.count()
        
        # Pagination
        offset = (page - 1) * limit
        salons = query.order_by(Salon.salon_rating.desc(), Salon.salon_name.asc()).offset(offset).limit(limit).all()
        
        total_pages = math.ceil(total / limit)
        
        return SalonListResponse(
            salons=salons,
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
            detail=f"Server xatoligi: {str(e)}"
        )

@router.post("/{salon_id}/photos", response_model=StandardResponse)
async def upload_salon_photos(
    salon_id: str,
    photo_data: PhotoUploadRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Salon rasmlari yuklash"""
    try:
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon topilmadi"
            )
        
        current_photos = salon.salon_photos or []
        updated_photos = current_photos + photo_data.photos
        
        salon.salon_photos = updated_photos
        db.commit()
        
        return StandardResponse(
            success=True,
            message="Rasmlar muvaffaqiyatli yuklandi",
            data={
                "salon_id": salon_id,
                "salon_photos": updated_photos,
                "total_photos": len(updated_photos)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server xatoligi: {str(e)}"
        )

@router.delete("/{salon_id}/photos", response_model=StandardResponse)
async def delete_salon_photo(
    salon_id: str,
    photo_data: PhotoDeleteRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Salon rasmini o'chirish"""
    try:
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon topilmadi"
            )
        
        current_photos = salon.salon_photos or []
        
        if photo_data.photo_index >= len(current_photos):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Noto'g'ri rasm indeksi"
            )
        
        # Remove photo at specified index
        updated_photos = current_photos[:photo_data.photo_index] + current_photos[photo_data.photo_index + 1:]
        
        salon.salon_photos = updated_photos
        db.commit()
        
        return StandardResponse(
            success=True,
            message="Rasm muvaffaqiyatli o'chirildi",
            data={
                "salon_id": salon_id,
                "salon_photos": updated_photos,
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
            detail=f"Server xatoligi: {str(e)}"
        )