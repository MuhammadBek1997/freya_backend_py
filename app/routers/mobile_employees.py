from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Union

from app.database import get_db
from app.i18nMini import get_translation
from app.models.employee import Employee, EmployeeComment
from app.models.salon import Salon


router = APIRouter(prefix="/mobile/employees", tags=["Mobile Employees"])


@router.get("/salon/{salon_id}")
async def get_employees_by_salon_mobile(
    salon_id: str,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Berilgan salon uchun xodimlar ro'yxati.

    Response format:
    - id: string
    - name: string
    - avatar: string (avatar_url)
    - workType: string (profession)
    - rate: float (rating)
    - reviewsCount: int (employee comments count)
    """

    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    employees: List[Employee] = (
        db.query(Employee)
        .filter(Employee.salon_id == salon_id, Employee.is_active == True)
        .all()
    )

    if not employees:
        return []

    # Preload review counts per employee in one query
    counts = (
        db.query(EmployeeComment.employee_id, func.count(EmployeeComment.id))
        .filter(EmployeeComment.employee_id.in_([e.id for e in employees]))
        .group_by(EmployeeComment.employee_id)
        .all()
    )
    count_map = {emp_id: int(cnt or 0) for emp_id, cnt in counts}

    def _full_name(e: Employee) -> str:
        if e.surname:
            return f"{e.name} {e.surname}".strip()
        return e.name or ""

    return [
        {
            "id": str(e.id),
            "name": _full_name(e),
            "avatar": e.avatar_url,
            "workType": e.profession,
            "rate": float(e.rating) if e.rating is not None else 0.0,
            "reviewsCount": count_map.get(e.id, 0),
        }
        for e in employees
    ]