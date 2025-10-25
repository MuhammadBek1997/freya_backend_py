from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, Union, List
import json
from app.database import get_db
from app.i18nMini import get_translation
from app.models.salon import Salon
from app.models.user_favourite_salon import UserFavouriteSalon
from app.schemas.salon import MobileSalonListResponse

# Reuse helpers from mobile salon router to keep item shape consistent
from app.routers.salon_mobile import build_mobile_item, calculate_distance



router = APIRouter(prefix="/mobile/defaults", tags=["Mobile Defaults"])

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
@router.get("/filter", response_model=MobileSalonListResponse)
async def filter_with_defaults_mobile(
    # DEFAULT_SALON_TYPES yuborishning 3 usulini qo'llab-quvvatlaymiz
    types: Optional[str] = Query(None, description="Vergul bilan ajratilgan turlar (masalan: beauty_salon,yoga)"),
    types_list: Optional[List[str]] = Query(
        None,
        description="Bir nechta query paramlari sifatida: ?types_list=beauty_salon&types_list=yoga",
    ),
    types_json: Optional[str] = Query(
        None,
        description="DEFAULT_SALON_TYPES formatidagi JSON massiv (string sifatida)",
    ),
    # DEFAULT_SALON_COMFORT yuborishning 3 usuli
    comforts: Optional[str] = Query(
        None,
        description="Vergul bilan ajratilgan comfort nomlari (masalan: parking,cafee,onlyFemale)",
    ),
    comforts_list: Optional[List[str]] = Query(
        None,
        description="Takroriy paramlar: ?comforts_list=parking&comforts_list=water",
    ),
    comforts_json: Optional[str] = Query(
        None,
        description="DEFAULT_SALON_COMFORT formatidagi JSON massiv (string sifatida)",
    ),
    # Yangi filtrlar
    top: Optional[bool] = Query(None, description="Top salonlarni ko'rsatish (is_top=True)"),
    discount: Optional[bool] = Query(None, description="Chegirmali salonlarni ko'rsatish (salon_sale mavjud)"),
    recommended: Optional[bool] = Query(None, description="Tavsiya etilgan salonlarni ko'rsatish (yuqori rating)"),
    isLiked: Optional[bool] = Query(None, description="Foydalanuvchi like bosgan salonlar (userId kerak)"),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    radius: float = Query(10.0, ge=0.1, le=100),
    distance: Optional[float] = Query(None, ge=0.1, le=100, description="Masofa bo'yicha filtr (km)"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    is_private: Optional[str] = Query(''),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    userId: Optional[str] = Query(None),
):
    """DEFAULT_SALON_TYPES va DEFAULT_SALON_COMFORT asosida alohida routerda filtr"""
    try:
        query = db.query(Salon).filter(and_(Salon.is_active == True, Salon.location.isnot(None)))

        if is_private != '':
            is_private_value = is_private.lower() == 'true'
            query = query.filter(Salon.private_salon == is_private_value)

        salons: List[Salon] = query.all()

        # Distance filtering (if coordinates provided)
        if latitude is not None and longitude is not None:
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                raise HTTPException(status_code=400, detail=get_translation(language, "errors.400"))
            use_radius = float(distance) if distance is not None else float(radius)
            nearby: List[Salon] = []
            for salon in salons:
                try:
                    if salon.location and 'lat' in salon.location and 'lng' in salon.location:
                        s_lat = float(salon.location['lat'])
                        s_lng = float(salon.location['lng'])
                        d_km = calculate_distance(float(latitude), float(longitude), s_lat, s_lng)
                        if d_km <= use_radius:
                            nearby.append(salon)
                except Exception:
                    continue
            salons = nearby

        # Types filtering: 3 usuldan kelgan tanlovlarni birlashtiramiz
        selected_types: List[str] = []
        if types_list:
            selected_types = [t.strip().lower() for t in types_list if t]
        elif types:
            selected_types = [t.strip().lower() for t in types.split(',') if t.strip()]
        elif types_json:
            try:
                arr = json.loads(types_json)
                if isinstance(arr, list):
                    selected_types = [
                        str(x.get('type', '')).strip().lower()
                        for x in arr
                        if isinstance(x, dict) and x.get('selected')
                    ]
            except Exception:
                selected_types = []

        if selected_types:
            filtered: List[Salon] = []
            for s in salons:
                try:
                    st = s.salon_types or []
                    chosen = [t.get("type", "").lower() for t in st if t.get("selected")]
                    if any(t in chosen for t in selected_types):
                        filtered.append(s)
                except Exception:
                    continue
            salons = filtered

        # Comfort filtering: 3 usuldan + eski flaglar bilan birlashtiramiz
        selected_comforts: List[str] = []
        if comforts_list:
            selected_comforts = [c.strip().lower() for c in comforts_list if c]
        elif comforts:
            selected_comforts = [c.strip().lower() for c in comforts.split(',') if c.strip()]
        elif comforts_json:
            try:
                arr = json.loads(comforts_json)
                if isinstance(arr, list):
                    selected_comforts = [
                        str(x.get('name', '')).strip().lower()
                        for x in arr
                        if isinstance(x, dict) and x.get('isActive')
                    ]
            except Exception:
                selected_comforts = []

        # Eski boolean flaglar olib tashlandi; faqat comforts*, types* paramlar ishlatiladi

        # Alias xaritasi (canonical -> aliases)
        alias_map = {
            'parking': [],
            'cafee': ['coffee'],
            'onlyfemale': ['onlyFemale', 'onlyWoman', 'onlyWomen'],
            'water': [],
            'pets': [],
            'bath': ['shower'],
            'towel': [],
            'kids': ['children_service'],
        }

        # Comfortlar bo'yicha AND mantiqda filtrlash
        for c in selected_comforts:
            key = c.lower()
            # canonical keylar
            canonical = key
            if key == 'onlyfemale':
                canonical = 'onlyFemale'
            elif key == 'cafee':
                canonical = 'cafee'
            elif key == 'kids':
                canonical = 'kids'
            elif key == 'bath':
                canonical = 'bath'
            # aliaslar
            aliases = alias_map.get(key, [])
            salons = [s for s in salons if _amenity_flag(s, canonical, aliases=aliases)]

        # Eski boolean comfort flaglar bilan alohida filtrlash ham olib tashlandi

        # Top salonlar filtri
        if top is True:
            salons = [s for s in salons if s.is_top is True]

        # Chegirmali salonlar filtri
        if discount is True:
            salons = [s for s in salons if s.salon_sale is not None and len(s.salon_sale) > 0]

        # Tavsiya etilgan salonlar filtri (yuqori rating)
        if recommended is True:
            salons = [s for s in salons if s.salon_rating is not None and s.salon_rating >= 4.0]

        # Foydalanuvchi like bosgan salonlar filtri
        if isLiked is not None:
            if not userId:
                raise HTTPException(status_code=400, detail="isLiked filtri uchun userId talab qilinadi")
            filtered = []
            for s in salons:
                try:
                    is_fav = db.query(UserFavouriteSalon).filter(
                        UserFavouriteSalon.user_id == userId,
                        UserFavouriteSalon.salon_id == str(s.id)
                    ).first() is not None
                    if (isLiked and is_fav) or ((isLiked is False) and (not is_fav)):
                        filtered.append(s)
                except Exception:
                    continue
            salons = filtered

        total = len(salons)
        offset = (page - 1) * limit
        paginated = salons[offset: offset + limit]
        items = [build_mobile_item(s, language, db, userId) for s in paginated]

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
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail=get_translation(language, "errors.500"))