from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, asc, desc
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.i18nMini import get_translation
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.models.salon import Salon
from app.models.user_chat import UserChat
from app.models.message import Message


router = APIRouter(prefix="/messages", tags=["messages"])


# GET /api/messages/conversations - Barcha suhbatlar
@router.get("/conversations", status_code=status.HTTP_200_OK)
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Foydalanuvchi uchun barcha suhbatlar ro'yxati"""

    chats: List[UserChat] = (
        db.query(UserChat)
        .filter(UserChat.user_id == current_user.id)
        .order_by(desc(UserChat.last_message_time))
        .all()
    )

    data = []
    for chat in chats:
        # Hisoblash: o'qilmagan xabarlar soni (foydalanuvchi uchun)
        unread_count = (
            db.query(Message)
            .filter(
                Message.user_chat_id == chat.id,
                Message.receiver_id == current_user.id,
                Message.is_read == False,
            )
            .count()
        )

        participant = None
        if chat.employee_id:
            employee = db.query(Employee).filter(Employee.id == chat.employee_id).first()
            participant = {
                "type": "employee",
                "id": chat.employee_id,
                "name": getattr(employee, "name", None),
            }
        elif chat.salon_id:
            salon = db.query(Salon).filter(Salon.id == chat.salon_id).first()
            participant = {
                "type": "salon",
                "id": chat.salon_id,
                "name": getattr(salon, "name", None),
            }

        data.append(
            {
                "chat_id": chat.id,
                "chat_type": chat.chat_type,
                "participant": participant,
                "last_message": chat.last_message,
                "last_message_time": chat.last_message_time,
                "unread_count": unread_count,
            }
        )

    return {
        "success": True,
        "message": get_translation(language, "messages.conversationsFetched"),
        "data": data,
    }


# GET /api/messages/conversation/:userId - Bitta suhbat xabarlari
@router.get("/conversation/{user_id}", status_code=status.HTTP_200_OK)
async def get_conversation_messages(
    user_id: str,
    chat_with_type: Optional[str] = Query(None, description="employee | salon"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Bitta suhbatdagi xabarlar (employee yoki salon bilan)"""

    # Topish: mavjud chat
    chat_q = db.query(UserChat).filter(UserChat.user_id == current_user.id)
    if chat_with_type == "employee":
        chat_q = chat_q.filter(UserChat.employee_id == user_id, UserChat.chat_type == "user_employee")
    elif chat_with_type == "salon":
        chat_q = chat_q.filter(UserChat.salon_id == user_id, UserChat.chat_type == "user_salon")
    else:
        chat_q = chat_q.filter(or_(UserChat.employee_id == user_id, UserChat.salon_id == user_id))

    chat = chat_q.first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    messages = (
        db.query(Message)
        .filter(Message.user_chat_id == chat.id)
        .order_by(asc(Message.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    data = [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "sender_type": m.sender_type,
            "receiver_id": m.receiver_id,
            "receiver_type": m.receiver_type,
            "message_text": m.message_text,
            "message_type": m.message_type,
            "file_url": m.file_url,
            "is_read": m.is_read,
            "created_at": m.created_at,
        }
        for m in messages
    ]

    return {
        "success": True,
        "message": get_translation(language, "messages.conversationFetched"),
        "data": {
            "chat_id": chat.id,
            "chat_type": chat.chat_type,
            "messages": data,
        },
    }


class SendMessageRequest(BaseModel):
    receiver_id: str
    receiver_type: str  # "employee" yoki "salon"
    message_text: str
    message_type: Optional[str] = "text"
    file_url: Optional[str] = None


# POST /api/messages/send - Xabar yuborish
@router.post("/send", status_code=status.HTTP_201_CREATED)
async def send_message(
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Xabar yuborish (foydalanuvchidan employee yoki salon ga)"""

    # Chatni topish yoki yaratish
    receiver_id = payload.receiver_id
    receiver_type = payload.receiver_type
    message_text = payload.message_text
    message_type = payload.message_type or "text"
    file_url = payload.file_url

    if receiver_type == "employee":
        chat = (
            db.query(UserChat)
            .filter(
                UserChat.user_id == current_user.id,
                UserChat.employee_id == receiver_id,
                UserChat.chat_type == "user_employee",
            )
            .first()
        )
        if not chat:
            # Employee mavjudligini tekshirish
            employee = db.query(Employee).filter(Employee.id == receiver_id).first()
            if not employee:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=get_translation(language, "errors.404"),
                )
            chat = UserChat(
                user_id=current_user.id,
                employee_id=receiver_id,
                chat_type="user_employee",
                last_message=None,
                last_message_time=None,
            )
            db.add(chat)
            db.flush()
    else:  # salon
        chat = (
            db.query(UserChat)
            .filter(
                UserChat.user_id == current_user.id,
                UserChat.salon_id == receiver_id,
                UserChat.chat_type == "user_salon",
            )
            .first()
        )
        if not chat:
            salon = db.query(Salon).filter(Salon.id == receiver_id).first()
            if not salon:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=get_translation(language, "errors.404"),
                )
            chat = UserChat(
                user_id=current_user.id,
                salon_id=receiver_id,
                chat_type="user_salon",
                last_message=None,
                last_message_time=None,
            )
            db.add(chat)
            db.flush()

    # Xabar yaratish
    new_message = Message(
        user_chat_id=chat.id,
        sender_id=current_user.id,
        sender_type="user",
        receiver_id=receiver_id,
        receiver_type=receiver_type,
        message_text=message_text,
        message_type=message_type,
        file_url=file_url,
        is_read=False,
    )

    # Chat meta ma'lumotlarini yangilash
    chat.last_message = message_text
    chat.last_message_time = datetime.utcnow()

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {
        "success": True,
        "message": get_translation(language, "messages.sent"),
        "data": {
            "id": new_message.id,
            "chat_id": chat.id,
            "sender_id": new_message.sender_id,
            "receiver_id": new_message.receiver_id,
            "message_text": new_message.message_text,
            "created_at": new_message.created_at,
        },
    }


# PUT /api/messages/conversation/:userId/mark-read - O'qilgan deb belgilash
@router.put("/conversation/{user_id}/mark-read", status_code=status.HTTP_200_OK)
async def mark_conversation_read(
    user_id: str,
    chat_with_type: Optional[str] = Query(None, description="employee | salon"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Berilgan suhbatdagi o'qilmagan xabarlarni o'qilgan deb belgilash"""

    chat_q = db.query(UserChat).filter(UserChat.user_id == current_user.id)
    if chat_with_type == "employee":
        chat_q = chat_q.filter(UserChat.employee_id == user_id, UserChat.chat_type == "user_employee")
    elif chat_with_type == "salon":
        chat_q = chat_q.filter(UserChat.salon_id == user_id, UserChat.chat_type == "user_salon")
    else:
        chat_q = chat_q.filter(or_(UserChat.employee_id == user_id, UserChat.salon_id == user_id))

    chat = chat_q.first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    # Foydalanuvchi uchun o'qilmagan xabarlarni o'qilgan qilish
    db.query(Message).filter(
        Message.user_chat_id == chat.id,
        Message.receiver_id == current_user.id,
        Message.is_read == False,
    ).update({Message.is_read: True})

    # O'qilmagan sonini nolga tushirish (hisoblashni soddalashtirish)
    chat.unread_count = 0

    db.commit()

    return {
        "success": True,
        "message": get_translation(language, "messages.markedRead"),
        "data": {"chat_id": chat.id},
    }


# === Employee tarafidagi xabarlar uchun endpointlar ===

class EmployeeSendMessageRequest(BaseModel):
    receiver_id: str  # foydalanuvchi ID
    message_text: str
    message_type: Optional[str] = "text"
    file_url: Optional[str] = None


# GET /api/messages/employee/conversations - Xodim uchun barcha suhbatlar
@router.get("/employee/conversations", status_code=status.HTTP_200_OK)
async def get_employee_conversations(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Xodim (employee) uchun barcha suhbatlar ro'yxati"""

    # Faqat employee roliga ruxsat
    if not isinstance(current_user, Employee):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=get_translation(language, "errors.403"))

    chats: List[UserChat] = (
        db.query(UserChat)
        .filter(UserChat.employee_id == current_user.id, UserChat.chat_type == "user_employee")
        .order_by(desc(UserChat.last_message_time))
        .all()
    )

    data = []
    for chat in chats:
        # Hisoblash: o'qilmagan xabarlar soni (employee uchun)
        unread_count = (
            db.query(Message)
            .filter(
                Message.user_chat_id == chat.id,
                Message.receiver_id == current_user.id,
                Message.is_read == False,
            )
            .count()
        )

        participant = None
        if chat.user_id:
            user = db.query(User).filter(User.id == chat.user_id).first()
            participant = {
                "type": "user",
                "id": chat.user_id,
                "name": getattr(user, "full_name", None) or getattr(user, "username", None),
            }

        data.append(
            {
                "chat_id": chat.id,
                "chat_type": chat.chat_type,
                "participant": participant,
                "last_message": chat.last_message,
                "last_message_time": chat.last_message_time,
                "unread_count": unread_count,
            }
        )

    return {
        "success": True,
        "message": get_translation(language, "messages.conversationsFetched"),
        "data": data,
    }


# GET /api/messages/employee/conversation/:userId - Xodim uchun bitta suhbat xabarlari
@router.get("/employee/conversation/{user_id}", status_code=status.HTTP_200_OK)
async def get_employee_conversation_messages(
    user_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Xodim va berilgan foydalanuvchi orasidagi xabarlar"""

    if not isinstance(current_user, Employee):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=get_translation(language, "errors.403"))

    chat = (
        db.query(UserChat)
        .filter(
            UserChat.user_id == user_id,
            UserChat.employee_id == current_user.id,
            UserChat.chat_type == "user_employee",
        )
        .first()
    )

    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))

    messages = (
        db.query(Message)
        .filter(Message.user_chat_id == chat.id)
        .order_by(asc(Message.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    data = [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "sender_type": m.sender_type,
            "receiver_id": m.receiver_id,
            "receiver_type": m.receiver_type,
            "message_text": m.message_text,
            "message_type": m.message_type,
            "file_url": m.file_url,
            "is_read": m.is_read,
            "created_at": m.created_at,
        }
        for m in messages
    ]

    return {
        "success": True,
        "message": get_translation(language, "messages.conversationFetched"),
        "data": {"chat_id": chat.id, "chat_type": chat.chat_type, "messages": data},
    }


# PUT /api/messages/employee/conversation/:userId/mark-read - Xodim tomonidan o'qilgan deb belgilash
@router.put("/employee/conversation/{user_id}/mark-read", status_code=status.HTTP_200_OK)
async def mark_employee_conversation_read(
    user_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Xodim uchun berilgan suhbatdagi o'qilmagan xabarlarni o'qilgan deb belgilash"""

    if not isinstance(current_user, Employee):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=get_translation(language, "errors.403"))

    chat = (
        db.query(UserChat)
        .filter(
            UserChat.user_id == user_id,
            UserChat.employee_id == current_user.id,
            UserChat.chat_type == "user_employee",
        )
        .first()
    )

    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))

    # Xodim uchun o'qilmagan xabarlarni o'qilgan qilish
    db.query(Message).filter(
        Message.user_chat_id == chat.id,
        Message.receiver_id == current_user.id,
        Message.is_read == False,
    ).update({Message.is_read: True})

    chat.unread_count = 0
    db.commit()

    return {
        "success": True,
        "message": get_translation(language, "messages.markedRead"),
        "data": {"chat_id": chat.id},
    }


# POST /api/messages/employee/send - Xodimdan foydalanuvchiga xabar yuborish
@router.post("/employee/send", status_code=status.HTTP_201_CREATED)
async def employee_send_message(
    payload: EmployeeSendMessageRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Xodimdan foydalanuvchiga xabar yuborish"""

    if not isinstance(current_user, Employee):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=get_translation(language, "errors.403"))

    receiver_id = payload.receiver_id  # user ID
    message_text = payload.message_text
    message_type = payload.message_type or "text"
    file_url = payload.file_url

    # Chatni topish yoki yaratish (user_employee)
    chat = (
        db.query(UserChat)
        .filter(
            UserChat.user_id == receiver_id,
            UserChat.employee_id == current_user.id,
            UserChat.chat_type == "user_employee",
        )
        .first()
    )

    if not chat:
        # Foydalanuvchi mavjudligini tekshirish
        user = db.query(User).filter(User.id == receiver_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"))

        chat = UserChat(
            user_id=receiver_id,
            employee_id=current_user.id,
            chat_type="user_employee",
            last_message=None,
            last_message_time=None,
        )
        db.add(chat)
        db.flush()

    # Xabar yaratish
    new_message = Message(
        user_chat_id=chat.id,
        sender_id=current_user.id,
        sender_type="employee",
        receiver_id=receiver_id,
        receiver_type="user",
        message_text=message_text,
        message_type=message_type,
        file_url=file_url,
        is_read=False,
    )

    chat.last_message = message_text
    chat.last_message_time = datetime.utcnow()

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {
        "success": True,
        "message": get_translation(language, "messages.sent"),
        "data": {
            "id": new_message.id,
            "chat_id": chat.id,
            "sender_id": new_message.sender_id,
            "receiver_id": new_message.receiver_id,
            "message_text": new_message.message_text,
            "created_at": new_message.created_at,
        },
    }