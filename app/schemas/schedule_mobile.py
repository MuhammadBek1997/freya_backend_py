from typing import List, Optional, Union
from pydantic import BaseModel


class MobileEmployeeItem(BaseModel):
    id: str
    name: Optional[str] = None
    reviewsCount: Optional[int] = 0
    rate: Optional[Union[float, int]] = 0.0
    workType: Optional[str] = None
    avatar: Optional[str] = None

class TimeslotItem(BaseModel):
    time: str
    empty_slot: int

class MobileScheduleServiceItem(BaseModel):
    id: str
    salon_id: str
    name: str
    title: Optional[str] = None
    price: float
    date: Optional[str] = None
    day: Optional[str] = None
    employees: List[MobileEmployeeItem] = []
    times: List[TimeslotItem] = []
    onlyCard: bool = False



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