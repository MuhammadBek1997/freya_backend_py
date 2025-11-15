from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Union
import math
import uuid

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.i18nMini import get_translation
from app.models.notif import Notif
from app.models.notification import Notification
from app.models.salon_comment import SalonComment
from app.models.user import User

router = APIRouter(
    prefix="/mobile/notif",
    tags=["Salon Mobile Notifications"],
    responses={404: {"description": "Not found"}},
)

@router.get("/is_subscribed", summary="Check if user is subscribed to notifications")
async def check_notif(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Check if the current user is subscribed to notifications"""
    if not current_user or not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi aniqlanmadi"
        )
    
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi"
        )
    is_subscribed = bool(db.query(Notif).filter(Notif.user_id == user.id).first() is not None)
    return {"is_subscribed": is_subscribed}

@router.post("/subscribe", summary="Subscribe user to notifications")
async def subscribe_notif(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Subscribe the current user to notifications"""
    if not current_user or not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi aniqlanmadi"
        )
    
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi"
        )
    
    existing_notif = db.query(Notif).filter(Notif.user_id == user.id).first()
    if existing_notif:
        return {"message": "Foydalanuvchi allaqachon obuna bo'lgan"}
    
    new_notif = Notif(
        id=str(uuid.uuid4()),
        user_id=user.id
    )
    db.add(new_notif)
    db.commit()
    return {"message": "Foydalanuvchi muvaffaqiyatli obuna bo'ldi"}

@router.post("/unsubscribe", summary="Unsubscribe user from notifications")
async def unsubscribe_notif(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Unsubscribe the current user from notifications"""
    if not current_user or not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi aniqlanmadi"
        )
    
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi"
        )
    
    existing_notif = db.query(Notif).filter(Notif.user_id == user.id).first()
    if not existing_notif:
        return {"message": "UserNotexist"}
    
    db.delete(existing_notif)
    db.commit()
    return {"message": "Foydalanuvchi muvaffaqiyatli obunadan chiqdi"}


@router.get("/list", summary="Get user notifications")
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    only_unread: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user or not current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi aniqlanmadi")
    offset = (page - 1) * limit
    query = db.query(Notification).filter(Notification.user_id == str(current_user.id))
    count_query = db.query(func.count(Notification.id)).filter(Notification.user_id == str(current_user.id))
    if only_unread:
        query = query.filter(Notification.is_read == False)
        count_query = count_query.filter(Notification.is_read == False)
    total = count_query.scalar()
    notifs = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    data = [
        {
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": n.is_read,
            "data": n.data,
            "created_at": n.created_at.isoformat() if getattr(n, "created_at", None) else None,
        }
        for n in notifs
    ]
    return {
        "success": True,
        "data": data,
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit},
    }


@router.post("/{notif_id}/read", summary="Mark notification as read")
async def mark_notification_read(
    notif_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user or not current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi aniqlanmadi")
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == str(current_user.id)).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notif topilmadi")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return {"success": True, "data": {"id": str(notif.id), "is_read": notif.is_read}}