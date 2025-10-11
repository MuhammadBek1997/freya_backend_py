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