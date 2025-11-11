from typing import Dict, Set, Any, Optional, List
import json
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from app.auth.jwt_utils import JWTUtils
from app.database import SessionLocal
from app.models.user import User
from app.models.employee import Employee
from app.models.salon import Salon
from app.models.user_chat import UserChat
from app.models.message import Message
from app.models.notification import Notification
from app.models.notif import Notif


router = APIRouter(prefix="/api", tags=["WS"])


class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        self.rooms.setdefault(room_id, set()).add(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        try:
            if room_id in self.rooms:
                self.rooms[room_id].discard(websocket)
                if not self.rooms[room_id]:
                    self.rooms.pop(room_id, None)
        except Exception:
            pass

    async def broadcast(self, room_id: str, message: Dict[str, Any]):
        """Broadcast JSON message to all connections in the room."""
        payload = json.dumps(message, default=str)
        for ws in list(self.rooms.get(room_id, set())):
            try:
                await ws.send_text(payload)
            except Exception:
                # Drop broken connections
                self.disconnect(room_id, ws)


def _now_local_iso() -> str:
    """Return current time ISO string with +05:00 offset (Asia/Tashkent)."""
    try:
        tz = timezone(timedelta(hours=5))
        return datetime.now(tz).isoformat()
    except Exception:
        # Fallback to UTC if timezone fails
        return datetime.utcnow().isoformat()


class WSChatInfoResponse(BaseModel):
    endpoint: str
    params: Dict[str, str]
    message_example: Dict[str, Any]
    notes: List[str]
    usage_steps: List[str]
    events: Dict[str, Any]
    restrictions: List[str]
    multi_chat: List[str]
    ws_examples: Dict[str, str]
    errors: Dict[str, str]


@router.get("/ws/chat/info", response_model=WSChatInfoResponse)
async def ws_chat_info():
    """Swagger uchun WebSocket ulanish ma'lumotlari."""
    return WSChatInfoResponse(
        endpoint="/api/ws/chat",
        params={
            "token": "JWT access token (majburiy)",
            "receiver_id": "Qarshi tomon ID (user/employee/salon)",
            "receiver_type": "employee | salon | user",
        },
        message_example={
            "message_text": "Salom!",
            "message_type": "text",
            "file_url": None,
            "event": "message | mark_read",
        },
        notes=[
            "WebSocket endpointlar OpenAPI/Swagger roʻyxatida ko'rinmaydi.",
            "Ulanish: ws://<host>/api/ws/chat?token=...&receiver_id=...&receiver_type=employee",
            "Foydalanuvchi → xodim/salon: receiver_type=employee|salon",
            "Xodim → foydalanuvchi: receiver_type=user",
            "Ulanishda server avtomatik ravishda oxirgi 50 ta xabarni 'history' event bilan yuboradi.",
            "Paginatsiya: limit default 50 (≤200), offset default 0; javobda pagination {limit, offset, total} keladi.",
            "O'qilgan deb belgilash: client {event: 'mark_read'} yuboradi, server 'read' hodisasini broadcast qiladi.",
            "Vaqtlar ISO formatda UTC+05:00 (Asia/Tashkent) offset bilan yuboriladi (join/notification 'time', message 'created_at_local').",
            "Notification sarlavhalari 3 tilda keladi: title (UZ), title_ru (RU), title_en (EN). UI tiliga mosini ko'rsating.",
        ],
        usage_steps=[
            "1) JWT token oling (login orqali).",
            "2) WS oching: ws://<host>/api/ws/chat?token=<JWT>&receiver_id=<ID>&receiver_type=employee|salon|user",
            "3) Xabar yuborish: {message_text, message_type='text'|'file'|... , file_url?}.",
            "4) O'qilgan deb belgilash: {event:'mark_read'} yuboring.",
            "5) Tarixni olish: {event:'history', limit:50, offset:0} — keyingi sahifa uchun offsetni oshiring (masalan 50, 100...).",
            "5) Employee faqat mavjud chatga ulanadi; yangi chatni boshlab yubora olmaydi.",
            "6) Salon birinchi xabarni yubora olmaydi; user boshlaydi.",
        ],
        events={
            "join": {
                "desc": "Room'ga qo'shilganda yuboriladi",
                "payload": {"event": "join", "room_id": "<chat_id>", "user_id": "<id>", "role": "user|employee", "time": "<ISO>"}
            },
            "message": {
                "desc": "Yangi xabar",
                "payload": {
                    "event": "message",
                    "room_id": "<chat_id>",
                    "message": {
                        "id": "<msg_id>", "sender_id": "<id>", "sender_type": "user|employee",
                        "receiver_id": "<id>", "receiver_type": "user|employee|salon",
                        "message_text": "...", "message_type": "text|file|...",
                        "file_url": None, "is_read": False, "created_at": "<ISO>", "created_at_local": "<ISO+05:00>"
                    }
                }
            },
            "read": {
                "desc": "O'qilgan deb belgilash broadcast",
                "trigger": {"client_send": {"event": "mark_read"}},
                "payload": {"event": "read", "room_id": "<chat_id>", "by_user_id": "<id>", "time": "<ISO>"}
            },
            "history": {
                "desc": "Xabarlar tarixini paginatsiya bilan olish",
                "trigger": {"client_send": {"event": "history", "limit": 50, "offset": 0}},
                "payload": {
                    "event": "history",
                    "room_id": "<chat_id>",
                    "items": [
                        {
                            "id": "<msg_id>", "sender_id": "<id>", "sender_type": "user|employee",
                            "receiver_id": "<id>", "receiver_type": "user|employee|salon",
                            "message_text": "...", "message_type": "text|file|...",
                            "file_url": None, "is_read": False, "created_at": "<ISO>", "created_at_local": "<ISO+05:00>"
                        }
                    ],
                    "pagination": {"limit": 50, "offset": 0, "total": 123}
                }
            },
            "notification": {
                "desc": "Yangi xabar haqida real-time bildirishnoma",
                "payload": {
                    "event": "notification",
                    "room_id": "<chat_id>",
                    "kind": "chat_message",
                    "receiver_type": "user|employee",
                    "title": "Yangi xabar",
                    "title_ru": "Новое сообщение",
                    "title_en": "New message",
                    "message": "...",
                    "to_user_id": "<user_id|null>",
                    "to_employee_id": "<employee_id|null>",
                    "unread_count": 3,
                    "time": "<ISO+05:00>"
                }
            }
        },
        restrictions=[
            "Employee birinchi bo'lib chat boshlay olmaydi (REST: 403, WS: ulanmaydi).",
            "Salon birinchi bo'lib yozolmaydi — faqat user boshlab yuborgan chatga javob berishi mumkin.",
            "WS ulanish har doim bitta chatga bog'lanadi (room_id = UserChat.id).",
        ],
        multi_chat=[
            "Bir foydalanuvchi bir nechta chat uchun alohida WS ochishi mumkin (har chat uchun bitta ulanish).",
            "Multi-room bir soketda qo'llanmagan; kerak bo'lsa join_room/leave_room eventlari bilan qo'shish mumkin.",
        ],
        ws_examples={
            "user_to_employee": "ws://<host>/api/ws/chat?token=<USER_JWT>&receiver_id=<EMP_ID>&receiver_type=employee",
            "user_to_salon": "ws://<host>/api/ws/chat?token=<USER_JWT>&receiver_id=<SALON_ID>&receiver_type=salon",
            "employee_to_user_existing": "ws://<host>/api/ws/chat?token=<EMP_JWT>&receiver_id=<USER_ID>&receiver_type=user",
            "send_message": "ws.send(JSON.stringify({ message_text: 'Salom!', message_type: 'text' }))",
            "mark_read": "ws.send(JSON.stringify({ event: 'mark_read' }))",
            "handle_notification_js": "ws.onmessage = (ev) => { const msg = JSON.parse(ev.data); if (msg.event === 'notification') { const title = (uiLang==='ru'? msg.title_ru : uiLang==='en' ? msg.title_en : msg.title); const toMe = (msg.receiver_type==='user' ? msg.to_user_id === myUserId : msg.to_employee_id === myEmployeeId); if (toMe) { showToast(title, msg.message); updateBadge(msg.unread_count); } } };",
            "handle_message_time_js": "ws.onmessage = (ev) => { const msg = JSON.parse(ev.data); if (msg.event==='message') { const tLocal = msg.message.created_at_local || msg.message.created_at; renderMessage(msg.message, tLocal); } };",
        },
        errors={
            "WS_1008_POLICY_VIOLATION": "Parametrlar yetarli emas, token noto'g'ri, yoki employee uchun chat mavjud emas.",
            "WS_1011_INTERNAL_ERROR": "Kutilmagan server xatosi.",
            "REST_403": "Employee birinchi bo'lib xabar yubora olmaydi.",
            "REST_404": "Qarshi tomon topilmadi yoki chat mavjud emas.",
        }
    )


manager = ConnectionManager()


def _serialize_message(m: Message) -> Dict[str, Any]:
    """Convert Message ORM to JSON-friendly dict."""
    return {
        "id": str(m.id),
        "sender_id": str(m.sender_id),
        "sender_type": str(m.sender_type),
        "receiver_id": str(m.receiver_id),
        "receiver_type": str(m.receiver_type),
        "message_text": m.message_text,
        "message_type": m.message_type,
        "file_url": m.file_url,
        "is_read": bool(m.is_read),
        "created_at": m.created_at.isoformat() if getattr(m, "created_at", None) else None,
        "created_at_local": (
            m.created_at.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5))).isoformat()
            if getattr(m, "created_at", None) else _now_local_iso()
        ),
    }


def _get_or_create_chat(db, current_id: str, current_role: str, receiver_id: str, receiver_type: str) -> Optional[UserChat]:
    """Find or create a UserChat between the current user and receiver."""
    if receiver_type not in {"employee", "salon", "user"}:
        return None

    # Map chat_type and query according to sender role
    if current_role == "user":
        if receiver_type == "employee":
            chat = (
                db.query(UserChat)
                .filter(
                    UserChat.user_id == current_id,
                    UserChat.employee_id == receiver_id,
                    UserChat.chat_type == "user_employee",
                )
                .first()
            )
            if not chat:
                # Validate receiver exists
                if not db.query(Employee).filter(Employee.id == receiver_id, Employee.is_active == True).first():
                    return None
                chat = UserChat(
                    user_id=current_id,
                    employee_id=receiver_id,
                    chat_type="user_employee",
                    last_message=None,
                    last_message_time=None,
                )
                db.add(chat)
                db.flush()
            return chat

        elif receiver_type == "salon":
            chat = (
                db.query(UserChat)
                .filter(
                    UserChat.user_id == current_id,
                    UserChat.salon_id == receiver_id,
                    UserChat.chat_type == "user_salon",
                )
                .first()
            )
            if not chat:
                if not db.query(Salon).filter(Salon.id == receiver_id, Salon.is_active == True).first():
                    return None
                chat = UserChat(
                    user_id=current_id,
                    salon_id=receiver_id,
                    chat_type="user_salon",
                    last_message=None,
                    last_message_time=None,
                )
                db.add(chat)
                db.flush()
            return chat

    elif current_role == "employee":
        # Employee faqat mavjud chatga ulanadi, yangi chatni boshlab yubora olmaydi
        if receiver_type == "user":
            chat = (
                db.query(UserChat)
                .filter(
                    UserChat.user_id == receiver_id,
                    UserChat.employee_id == current_id,
                    UserChat.chat_type == "user_employee",
                )
                .first()
            )
            if not chat:
                # Mavjud chat yo'q — ulanib bo'lmaydi
                return None
            return chat

    # Admin/private_admin not supported in this minimal WS chat
    return None


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket chat endpoint.

    Query params:
      - token: JWT access token (required)
      - receiver_id: chat partner id (required)
      - receiver_type: "employee" | "salon" | "user" (required)
    """
    # Extract query params
    token = websocket.query_params.get("token")
    receiver_id = websocket.query_params.get("receiver_id")
    receiver_type = websocket.query_params.get("receiver_type")

    if not token or not receiver_id or not receiver_type:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Verify token and resolve sender identity
    try:
        payload = JWTUtils.verify_token(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    current_id = str(payload.get("id"))
    current_role = str(payload.get("role"))
    if not current_id or current_role not in {"user", "employee"}:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db = SessionLocal()
    chat = None
    room_id = None
    try:
        chat = _get_or_create_chat(db, current_id, current_role, receiver_id, receiver_type)
        if not chat:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        room_id = str(chat.id)
        await manager.connect(room_id, websocket)

        # Notify join
        await manager.broadcast(room_id, {
            "event": "join",
            "room_id": room_id,
            "user_id": current_id,
            "role": current_role,
            "time": _now_local_iso()
        })

        # On connect: send latest 50 messages (pagination default)
        try:
            total_msgs = db.query(Message).filter(Message.user_chat_id == chat.id).count()
            default_limit = 50
            recent_msgs = (
                db.query(Message)
                .filter(Message.user_chat_id == chat.id)
                .order_by(Message.created_at.desc())
                .offset(0)
                .limit(default_limit)
                .all()
            )
            # Reverse to chronological order (oldest -> newest)
            items = [_serialize_message(m) for m in reversed(recent_msgs)]
            await websocket.send_text(json.dumps({
                "event": "history",
                "room_id": room_id,
                "items": items,
                "pagination": {
                    "limit": default_limit,
                    "offset": 0,
                    "total": total_msgs,
                }
            }, default=str))
        except Exception:
            # Ignore history send failures
            pass

        # Receive loop
        while True:
            data = await websocket.receive_text()
            try:
                parsed = json.loads(data)
            except Exception:
                # ignore malformed
                continue
            event_type = parsed.get("event") or "message"

            if event_type == "mark_read":
                # Mark all unread messages in this chat as read for current user
                db.query(Message).filter(
                    Message.user_chat_id == chat.id,
                    Message.receiver_id == current_id,
                    Message.is_read == False,
                ).update({Message.is_read: True})

                # Reset unread counter if used
                try:
                    chat.unread_count = 0
                except Exception:
                    pass

                db.commit()

                # Broadcast read receipt
                await manager.broadcast(room_id, {
                    "event": "read",
                    "room_id": room_id,
                    "by_user_id": current_id,
                    "time": _now_local_iso(),
                })

                continue

            if event_type == "history":
                # Client requests paginated history: {event:"history", offset?, limit?}
                try:
                    limit = parsed.get("limit") or 50
                    offset = parsed.get("offset") or 0
                    # Clamp values for safety
                    try:
                        limit = int(limit)
                        offset = int(offset)
                    except Exception:
                        limit = 50
                        offset = 0
                    if limit < 1:
                        limit = 50
                    if limit > 200:
                        limit = 200
                    if offset < 0:
                        offset = 0

                    total_msgs = db.query(Message).filter(Message.user_chat_id == chat.id).count()
                    msgs = (
                        db.query(Message)
                        .filter(Message.user_chat_id == chat.id)
                        .order_by(Message.created_at.desc())
                        .offset(offset)
                        .limit(limit)
                        .all()
                    )
                    items = [_serialize_message(m) for m in reversed(msgs)]
                    await websocket.send_text(json.dumps({
                        "event": "history",
                        "room_id": room_id,
                        "items": items,
                        "pagination": {
                            "limit": limit,
                            "offset": offset,
                            "total": total_msgs,
                        }
                    }, default=str))
                except Exception:
                    # Silently ignore history errors to keep WS alive
                    pass
                continue

            # Default: treat as a new chat message
            message_text = parsed.get("message_text")
            message_type = parsed.get("message_type") or "text"
            file_url = parsed.get("file_url")

            # Persist message
            new_message = Message(
                user_chat_id=chat.id,
                sender_id=current_id,
                sender_type=current_role,
                receiver_id=receiver_id,
                receiver_type=receiver_type,
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

            # Broadcast to room
            await manager.broadcast(room_id, {
                "event": "message",
                "room_id": room_id,
                "message": {
                    "id": str(new_message.id),
                    "sender_id": current_id,
                    "sender_type": current_role,
                    "receiver_id": receiver_id,
                    "receiver_type": receiver_type,
                    "message_text": message_text,
                    "message_type": message_type,
                    "file_url": file_url,
                    "is_read": False,
                    "created_at": new_message.created_at.isoformat() if new_message.created_at else None,
                    "created_at_local": (
                        new_message.created_at.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5))).isoformat()
                        if new_message.created_at else _now_local_iso()
                    ),
                }
            })

            # Build and persist notification (for user receivers only if subscribed)
            try:
                unread_count = db.query(Message).filter(
                    Message.user_chat_id == chat.id,
                    Message.receiver_id == receiver_id,
                    Message.is_read == False,
                ).count()

                if receiver_type == "user":
                    # Only create DB notification for users and when subscribed in Notif
                    is_subscribed = db.query(Notif).filter(Notif.user_id == receiver_id).first() is not None
                    if is_subscribed:
                        notif = Notification(
                            user_id=receiver_id,
                            title="Yangi xabar",
                            message=message_text or "",
                            type="info",
                            data={
                                "kind": "chat_message",
                                "chat_id": str(chat.id),
                                "sender_id": current_id,
                                "sender_type": current_role,
                                "unread_count": unread_count,
                            },
                        )
                        db.add(notif)
                        db.commit()

                # Broadcast a lightweight notification event to the room
                await manager.broadcast(room_id, {
                    "event": "notification",
                    "room_id": room_id,
                    "kind": "chat_message",
                    "receiver_type": receiver_type,
                    "title": "Yangi xabar",
                    "title_ru": "Новое сообщение",
                    "title_en": "New message",
                    "message": message_text,
                    "to_user_id": receiver_id if receiver_type == "user" else None,
                    "to_employee_id": receiver_id if receiver_type == "employee" else None,
                    "unread_count": unread_count,
                    "time": _now_local_iso(),
                })
            except Exception:
                # Do not fail WS on notification errors
                pass

    except WebSocketDisconnect:
        # Client disconnected
        pass
    except Exception:
        # On unexpected error, close gracefully
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
    finally:
        try:
            if room_id:
                manager.disconnect(room_id, websocket)
            db.close()
        except Exception:
            pass