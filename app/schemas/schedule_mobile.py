from typing import List, Optional
from pydantic import BaseModel


class MobileScheduleServiceItem(BaseModel):
    id: str
    salon_id: str
    name: str
    title: Optional[str] = None
    price: float
    date: Optional[str] = None
    day: Optional[str] = None
    employees: List[str] = []
    times: List[str] = []


class MobileScheduleListResponse(BaseModel):
    success: bool
    data: List[MobileScheduleServiceItem]
    pagination: Optional[dict] = None


class MobileScheduleFilters(BaseModel):
    directions: List[str] = []
    times: List[str] = []
    employees: List[str] = []


class MobileScheduleFiltersResponse(BaseModel):
    success: bool
    data: MobileScheduleFilters