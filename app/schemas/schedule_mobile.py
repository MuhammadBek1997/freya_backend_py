from typing import List, Optional, Union
from pydantic import BaseModel


class MobileEmployeeItem(BaseModel):
    id: str
    name: Optional[str] = None
    reviewsCount: Optional[int] = 0
    rate: Optional[Union[float, int]] = 0.0
    workType: Optional[str] = None
    avatar: Optional[str] = None
    works: Optional[int] = 0
    perWeek: Optional[int] = 0

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


# Per-day filters (7 kunlik har kun uchun alohida ro'yxat)
class MobileScheduleDailyFiltersItem(BaseModel):
    date: str
    avialable: bool = False
    # day: str
    directions: List[str] = []
    # times: List[str] = []
    employees: List["DailyEmployeeItem"] = []


class DailyEmployeeItem(BaseModel):
    id: str
    name: Optional[str] = None

class MobileEmployeeDayServicesItem(BaseModel):
    id: str
    salon_id: str
    name: str
    title: Optional[str] = None
    price: float = 0.0
    day: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class MobileScheduleDailyFiltersResponse(BaseModel):
    success: bool
    data: List[MobileScheduleDailyFiltersItem]


class MobileEmployeeWeeklyDayItem(BaseModel):
    date: str
    avialable: bool = False
    services: List[MobileEmployeeDayServicesItem] = []


class MobileEmployeeWeeklyResponse(BaseModel):
    success: bool
    data: List[MobileEmployeeWeeklyDayItem]
    employee: MobileEmployeeItem
    pagination: Optional[dict] = None