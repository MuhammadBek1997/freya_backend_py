from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from pathlib import Path
import json

router = APIRouter(prefix="/city", tags=["City"])

# Data loading
DATA_PATH = Path(__file__).resolve().parents[2] / 'city.json'
try:
    with DATA_PATH.open('r', encoding='utf-8') as f:
        _data = json.load(f)
        _districts: List[Dict[str, Any]] = _data.get('districts', [])
except Exception:
    _districts = []

# Schemas
class DistrictItem(BaseModel):
    id: int
    name: str

class DistrictListResponse(BaseModel):
    districts: List[DistrictItem]
    total: int


def _name_by_lang(item: Dict[str, Any], lang: str) -> str:
    lang = (lang or 'uz').lower()
    if lang not in ['uz', 'ru', 'en']:
        lang = 'uz'
    return item.get(lang) or item.get('uz') or ''


@router.get('/districts', response_model=DistrictListResponse)
async def get_districts(lang: Optional[str] = Query('uz')):
    districts = [
        DistrictItem(id=int(item.get('id')), name=_name_by_lang(item, lang))
        for item in _districts
        if item.get('id') is not None
    ]
    return DistrictListResponse(districts=districts, total=len(districts))


@router.get('/districts/{district_id}', response_model=DistrictItem)
async def get_district_by_id(district_id: int, lang: Optional[str] = Query('uz')):
    for item in _districts:
        try:
            if int(item.get('id')) == district_id:
                return DistrictItem(id=district_id, name=_name_by_lang(item, lang))
        except Exception:
            continue
    raise HTTPException(status_code=404, detail="District not found")