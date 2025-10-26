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
from app.auth.dependencies import get_current_user_optional
from app.models.user import User

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
    isLiked: Optional[bool] = Query(None, description="Foydalanuvchi like bosgan salonlar (token kerak)"),
    # News: 'top','new','nearby' vergul bilan ajratib yuboriladi
    news: Optional[str] = Query(None, description="News filter: 'top','new','nearby' (vergul bilan)"),
    # Possible: only_woman yoki all
    possible: Optional[str] = Query(None, description="Possible: 'only_woman' yoki 'all'"),
    # Search: salon nomi shu text bilan boshlansa
    search: Optional[str] = Query(None, description="Salon nomi uchun prefix qidiruv"),
    # Rate: oraliq qiymatlar qabul qilinadi; >5 bo'lsa e'tiborga olinmaydi
    rate: Optional[float] = Query(None, description="Reyting bo'yicha filtr (oraliq qiymatlar, >5 e'tibor qilinmaydi)"),
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
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """DEFAULT_SALON_TYPES va DEFAULT_SALON_COMFORT asosida alohida routerda filtr"""
    try:
        query = db.query(Salon).filter(and_(Salon.is_active == True, Salon.location.isnot(None)))

        if is_private != '':
            is_private_value = is_private.lower() == 'true'
            query = query.filter(Salon.private_salon == is_private_value)

        # Search by salon_name prefix (DB-level for performance)
        if search and search.strip():
            query = query.filter(Salon.salon_name.ilike(f"{search.strip()}%"))

        salons: List[Salon] = query.all()

        # News filter: faqat 'top','new','nearby' qiymatlarini qabul qiladi
        sort_by_new = False
        if news:
            tokens = [n.strip().lower() for n in news.split(',') if n.strip()]
            allowed = {"top", "new", "nearby"}
            invalid = [n for n in tokens if n not in allowed]
            if invalid:
                raise HTTPException(status_code=400, detail="news faqat 'top','new','nearby' qiymatlarini qabul qiladi")

            # nearby bo'lsa koordinatalar majburiy
            if "nearby" in tokens:
                if latitude is None or longitude is None:
                    raise HTTPException(status_code=400, detail="nearby uchun latitude va longitude kerak")
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

            # top bo'lsa top=True filtrini qo'llash
            if "top" in tokens:
                salons = [s for s in salons if s.is_top is True]

            # new bo'lsa created_at bo'yicha saralash (desc)
            if "new" in tokens:
                sort_by_new = True

        # Distance filtering (if coordinates provided), agar news=nearby ishlatilmagan bo'lsa
        if latitude is not None and longitude is not None and not (news and "nearby" in [n.strip().lower() for n in news.split(',') if n.strip()]):
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

        # Comfort filtering
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

        for c in selected_comforts:
            key = c.lower()
            key = c.lower()
            canonical = key
            if key == 'onlyfemale':
                canonical = 'onlyFemale'
            elif key == 'cafee':
                canonical = 'cafee'
            elif key == 'kids':
                canonical = 'kids'
            elif key == 'bath':
                canonical = 'bath'
            aliases = alias_map.get(key, [])
            salons = [s for s in salons if _amenity_flag(s, canonical, aliases=aliases)]

        # Possible filter (only_woman | all)
        if possible:
            p = possible.strip().lower()
            if p not in ("only_woman", "all"):
                raise HTTPException(status_code=400, detail="possible faqat 'only_woman' yoki 'all' bo'lishi mumkin")
            if p == "only_woman":
                salons = [s for s in salons if _amenity_flag(s, 'onlyFemale', aliases=['onlyWoman','onlyWomen'])]
            # 'all' bo'lsa hech narsa qilmaymiz

        # Top
        if top is True:
            salons = [s for s in salons if s.is_top is True]

        # Discount
        if discount is True:
            salons = [s for s in salons if s.salon_sale is not None and len(s.salon_sale) > 0]

        # Recommended
        if recommended is True:
            salons = [s for s in salons if s.salon_rating is not None and s.salon_rating >= 4.0]

        # new bo'lsa created_at bo'yicha saralash (desc)
        if sort_by_new:
            try:
                salons = sorted(salons, key=lambda s: getattr(s, 'created_at', None) or 0, reverse=True)
            except Exception:
                pass

        # Rate filter: oraliq qiymatlar (<=5) uchun ±0.5 interval
        if rate is not None:
            try:
                rate_val = float(rate)
            except Exception:
                rate_val = None
            if rate_val is not None and rate_val <= 5:
                lower = max(rate_val - 0.5, 0.0)
                upper = min(rate_val + 0.5, 5.0)
                filtered: List[Salon] = []
                for s in salons:
                    try:
                        r = s.salon_rating
                        if r is None:
                            continue
                        r_val = float(r)
                        if r_val >= lower and r_val <= upper:
                            filtered.append(s)
                    except Exception:
                        continue
                salons = filtered
            # rate > 5 bo'lsa e'tiborga olinmaydi (filtr qo'llanmaydi)

        # Liked filter via user token
        if isLiked is not None:
            if current_user is None:
                raise HTTPException(status_code=401, detail="isLiked filtri uchun foydalanuvchi token kerak")
            filtered = []
            for s in salons:
                try:
                    is_fav = db.query(UserFavouriteSalon).filter(
                        UserFavouriteSalon.user_id == str(current_user.id),
                        UserFavouriteSalon.salon_id == str(s.id)
                    ).first() is not None
                    if (isLiked and is_fav) or (isLiked is False and not is_fav):
                        filtered.append(s)
                except Exception:
                    continue
            salons = filtered

        total = len(salons)
        offset = (page - 1) * limit
        paginated = salons[offset: offset + limit]
        user_id_for_favorite = str(current_user.id) if current_user else userId
        items = [build_mobile_item(s, language, db, user_id_for_favorite) for s in paginated]

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