from fastapi import APIRouter, Depends, HTTPException, Header, status, Query
from sqlalchemy.orm import Session
from typing import Union, Optional, List

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.i18nMini import get_translation
from app.models.salon import Salon
from app.models.employee import Employee, EmployeeComment
from app.models.salon_comment import SalonComment
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentItem, CommentListResponse


router = APIRouter(prefix="/comments", tags=["Comments"])


def _user_display_name(user: Optional[User]) -> Optional[str]:
    if not user:
        return None
    return user.full_name or user.username or user.phone


@router.post(
    "/salon/{salon_id}",
    summary="Salonga comment qo'shish",
    description="X-User-language (uz|ru|en) headeriga ko'ra xabarlar i18n qilinadi.",
)
async def add_salon_comment(
    salon_id: str,
    request: CommentCreate,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    current_user: User = Depends(get_current_user),
):
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))
    current_user_id = current_user.id
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))

    comment = SalonComment(salon_id=salon_id, user_id=current_user_id, text=request.text, rating=request.rating)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "success": True,
        "data": CommentItem(
            id=str(comment.id),
            user_id=str(user.id),
            user_name=_user_display_name(user),
            text=comment.text,
            rating=int(comment.rating),
            created_at=comment.created_at,
        ),
    }


@router.get(
    "/salon/{salon_id}",
    response_model=CommentListResponse,
    summary="Salon commentlarini olish",
)
async def get_salon_comments(
    salon_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))

    total = db.query(SalonComment).filter(SalonComment.salon_id == salon_id).count()
    offset = (page - 1) * limit
    rows: List[SalonComment] = (
        db.query(SalonComment).filter(SalonComment.salon_id == salon_id).order_by(SalonComment.created_at.desc()).offset(offset).limit(limit).all()
    )

    # Preload all involved users
    user_ids = list({row.user_id for row in rows})
    users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    user_map = {u.id: u for u in users}

    items: List[CommentItem] = [
        CommentItem(
            id=str(row.id),
            user_id=str(row.user_id),
            user_name=_user_display_name(user_map.get(row.user_id)),
            text=row.text,
            rating=int(row.rating),
            created_at=row.created_at,
        )
        for row in rows
    ]

    return CommentListResponse(
        success=True,
        data=items,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    )


@router.post(
    "/employee/{employee_id}",
    summary="Xodimga comment qo'shish",
    description="X-User-language (uz|ru|en) headeriga ko'ra xabarlar i18n qilinadi.",
)
async def add_employee_comment(
    employee_id: str,
    request: CommentCreate,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
    current_user: User = Depends(get_current_user),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))
    current_user_id = current_user.id
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))

    comment = EmployeeComment(employee_id=employee_id, user_id=current_user_id, text=request.text, rating=request.rating)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "success": True,
        "data": CommentItem(
            id=str(comment.id),
            user_id=str(user.id),
            user_name=_user_display_name(user),
            text=comment.text,
            rating=int(comment.rating),
            created_at=comment.created_at,
            avatar_url=user.avatar_url,
        ),
    }


@router.get(
    "/employee/{employee_id}",
    response_model=CommentListResponse,
    summary="Xodim commentlarini olish",
)
async def get_employee_comments(
    employee_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))

    total = db.query(EmployeeComment).filter(EmployeeComment.employee_id == employee_id).count()
    offset = (page - 1) * limit
    rows: List[EmployeeComment] = (
        db.query(EmployeeComment).filter(EmployeeComment.employee_id == employee_id).order_by(EmployeeComment.created_at.desc()).offset(offset).limit(limit).all()
    )

    user_ids = list({row.user_id for row in rows})
    users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    user_map = {u.id: u for u in users}

    items: List[CommentItem] = [
        CommentItem(
            id=str(row.id),
            user_id=str(row.user_id),
            user_name=_user_display_name(user_map.get(row.user_id)),
            owner_avatar_url=user_map.get(row.user_id).avatar_url if user_map.get(row.user_id) else None,
            text=row.text,
            rating=int(row.rating),
            created_at=row.created_at,
        )
        for row in rows
    ]

    return CommentListResponse(
        success=True,
        data=items,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    )