from typing import Dict, Set, Any, Optional, List
import json
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends, Query as FastQuery, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from app.auth.jwt_utils import JWTUtils
from app.database import SessionLocal, get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.models.salon import Salon
from app.models.admin import Admin
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
                "id": "<msg_id>", "sender_id": "<id>", "sender_type": "user|employee|salon",
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
                            "id": "<msg_id>", "sender_id": "<id>", "sender_type": "user|employee|salon",
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
                    "receiver_type": "user|employee|salon",
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
            "admin_to_user_existing": "ws://<host>/api/ws/chat?token=<ADMIN_JWT>&receiver_id=<USER_ID>&receiver_type=user",
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

    elif current_role == "admin":
        if receiver_type == "user":
            # Admin bitta user bilan chatga ulanadi
            admin = db.query(Admin).filter(Admin.id == current_id, Admin.is_active == True).first()
            if not admin or not getattr(admin, "salon_id", None):
                return None
            chat = (
                db.query(UserChat)
                .filter(
                    UserChat.user_id == receiver_id,
                    UserChat.salon_id == str(admin.salon_id),
                    UserChat.chat_type == "user_salon",
                )
                .first()
            )
            if not chat:
                # Admin side: agar user avval yozmagan bo'lsa chat yaratib beramiz
                user_obj = db.query(User).filter(User.id == receiver_id).first()
                if not user_obj:
                    return None
                chat = UserChat(
                    user_id=receiver_id,
                    salon_id=str(admin.salon_id),
                    chat_type="user_salon",
                    last_message=None,
                    last_message_time=None,
                )
                db.add(chat)
                db.flush()
            return chat

    # Other roles not supported in this minimal WS chat
    return None


@router.get("/chat/list")
async def get_chat_list(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """
    Foydalanuvchi uchun chatlar ro'yxatini Message modelidan olish.
    (UserChat jadvalini ishlatmasdan)
    """
    try:
        user_id = str(current_user.id)
        role = getattr(current_user, "role", "user")
        salon_id = str(getattr(current_user, "salon_id", ""))

        # Admin uchun salon_id bo'yicha ham filtrlaymiz
        if role in ["admin", "superadmin", "salon_admin", "private_admin", "private_salon_admin"]:
            role_cond = or_(
                Message.sender_id == user_id,
                Message.receiver_id == user_id,
                Message.sender_id == salon_id,
                Message.receiver_id == salon_id,
                # Muhim: user salonga yozgan bo'lsa (receiver_id = salon_id),
                # lekin salon hali javob bermagan bo'lsa ham ko'rinishi kerak
                and_(Message.receiver_id == salon_id, Message.receiver_type == "salon")
            )
        else:
            role_cond = or_(
                Message.sender_id == user_id,
                Message.receiver_id == user_id
            )

        # Har bir chat_id uchun oxirgi xabarni topish subquery'si
        subquery = (
            db.query(
                Message.user_chat_id,
                func.max(Message.created_at).label("latest_at")
            )
            .filter(role_cond)
            .group_by(Message.user_chat_id)
            .subquery()
        )

        # Oxirgi xabarlarni va ularning ma'lumotlarini olish
        latest_msgs = (
            db.query(Message)
            .join(subquery, and_(
                Message.user_chat_id == subquery.c.user_chat_id,
                Message.created_at == subquery.c.latest_at
            ))
            .all()
        )

        result = []
        for msg in latest_msgs:
            try:
                chat_id = str(msg.user_chat_id)
                
                # Biz (current_user) kim ekanimizni aniqlaymiz: sender yoki receiver
                # (Admin holatida salon_id ham biz hisoblanamiz)
                is_sender = (str(msg.sender_id) == user_id) or (salon_id and str(msg.sender_id) == salon_id)
                
                if is_sender:
                    opponent_id = str(msg.receiver_id)
                    opponent_type = str(msg.receiver_type)
                else:
                    opponent_id = str(msg.sender_id)
                    opponent_type = str(msg.sender_type)

                # Qarshi tomon ismini olish
                opponent_name = "Unknown"
                if opponent_type == "user":
                    user_obj = db.query(User).filter(User.id == opponent_id).first()
                    if user_obj:
                        opponent_name = user_obj.full_name or user_obj.username or "User"
                elif opponent_type == "employee":
                    emp_obj = db.query(Employee).filter(Employee.id == opponent_id).first()
                    if emp_obj:
                        opponent_name = f"{emp_obj.name} {emp_obj.surname or ''}".strip() or "Employee"
                elif opponent_type == "salon" or opponent_type == "admin":
                    salon_obj = db.query(Salon).filter(Salon.id == opponent_id).first()
                    if salon_obj:
                        opponent_name = salon_obj.name or "Salon"
                
                # O'qilmagan xabarlar soni
                unread_count = db.query(Message).filter(
                    Message.user_chat_id == chat_id,
                    Message.receiver_id == (salon_id if (role == 'admin' and not is_sender) else user_id),
                    Message.is_read == False
                ).count()

                result.append({
                    "chat_id": chat_id,
                    "opponent_name": opponent_name,
                    "opponent_id": opponent_id,
                    "opponent_type": opponent_type,
                    "last_message": str(msg.message_text or ""),
                    "last_message_time": msg.created_at.isoformat() if msg.created_at else None,
                    "unread_count": unread_count
                })
            except Exception as e:
                print(f"Error processing message in chat list: {e}")
                continue

        # Vaqt bo'yicha saralash
        result.sort(key=lambda x: x["last_message_time"] or "", reverse=True)
        return {"success": True, "data": result}

    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR in get_chat_list: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/chat/history/{chat_id}")
async def get_chat_history(
    chat_id: str,
    limit: int = FastQuery(50, ge=1, le=200),
    offset: int = FastQuery(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """
    Chat xabarlari tarixini Message modelidan olish.
    (UserChat jadvalini ishlatmasdan)
    """
    user_id = str(current_user.id)
    role = getattr(current_user, "role", "user")
    salon_id = str(getattr(current_user, "salon_id", ""))

    # Xavfsizlik: user faqat o'zi qatnashgan chat xabarlarini ko'rishi kerak
    # Yoki admin o'z saloniga tegishli xabarlarni ko'ra oladi
    is_allowed = False
    
    # 1. User/Employee o'zi qatnashganligini tekshiramiz
    participant_check = db.query(Message).filter(
        Message.user_chat_id == chat_id,
        or_(
            Message.sender_id == user_id,
            Message.receiver_id == user_id
        )
    ).first()
    
    if participant_check:
        is_allowed = True
    
    # 2. Admin uchun salon_id bo'yicha tekshiramiz
    if not is_allowed and role in ["admin", "superadmin", "salon_admin", "private_admin", "private_salon_admin"]:
        if role == "superadmin":
            is_allowed = True
        elif salon_id:
            salon_check = db.query(Message).filter(
                Message.user_chat_id == chat_id,
                or_(
                    Message.sender_id == salon_id,
                    Message.receiver_id == salon_id
                )
            ).first()
            if salon_check:
                is_allowed = True

    if not is_allowed:
        # Agar hali xabar bo'lmasa, lekin chat yaratilgan bo'lsa (UserChat orqali),
        # bu yerda muammo bo'lishi mumkin. Lekin user "UserChat ishlatma" degan.
        # Shuning uchun faqat xabarlar bor chatlarni ko'ra oladi.
        raise HTTPException(status_code=403, detail="Sizda ushbu chatni ko'rishga ruxsat yo'q yoki chat hali bo'sh")

    total = db.query(Message).filter(Message.user_chat_id == chat_id).count()
    messages = (
        db.query(Message)
        .filter(Message.user_chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "success": True,
        "chat_id": chat_id,
        "items": [_serialize_message(m) for m in reversed(messages)],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total
        }
    }


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

    if not token or not receiver_type:
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
    # salon_admin ham admin kabi ishlaydi
    if current_role == "salon_admin":
        current_role = "admin"
    if not current_id or current_role not in {"user", "employee", "admin"}:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Admin+salon case da receiver_id shart emas; qolgan holatlarda talab qilinadi
    if not receiver_id and not (current_role == "admin" and receiver_type == "salon"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # ── Special case: Admin salon-level notification room ──────────────────
    # Admin receiver_type="salon" bilan ulanganda barcha salon xabarlarini eshitadi
    if current_role == "admin" and receiver_type == "salon":
        db2 = SessionLocal()
        salon_room_id = None
        try:
            admin_obj = db2.query(Admin).filter(Admin.id == current_id, Admin.is_active == True).first()
            if not admin_obj or not getattr(admin_obj, "salon_id", None):
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            salon_room_id = f"salon_{admin_obj.salon_id}"
            await manager.connect(salon_room_id, websocket)
            await manager.broadcast(salon_room_id, {
                "event": "join",
                "room_id": salon_room_id,
                "user_id": current_id,
                "role": "admin",
                "time": _now_local_iso(),
            })
            # Admin bu modda faqat notification qabul qiladi
            while True:
                try:
                    await websocket.receive_text()
                except Exception:
                    break
        except WebSocketDisconnect:
            pass
        except Exception:
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except Exception:
                pass
        finally:
            try:
                if salon_room_id:
                    manager.disconnect(salon_room_id, websocket)
                db2.close()
            except Exception:
                pass
        return
    # ───────────────────────────────────────────────────────────────────────

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
                # Admin uchun receiver_id = salon_id (admin_id emas)
                if current_role == "admin":
                    admin_obj = db.query(Admin).filter(Admin.id == current_id).first()
                    effective_receiver_id = str(admin_obj.salon_id) if admin_obj and getattr(admin_obj, "salon_id", None) else current_id
                else:
                    effective_receiver_id = current_id

                # Mark all unread messages in this chat as read
                db.query(Message).filter(
                    Message.user_chat_id == chat.id,
                    Message.receiver_id == effective_receiver_id,
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

            # Sender type normalization: admin -> salon
            sender_type_eff = "salon" if current_role == "admin" else current_role

            # Persist message
            new_message = Message(
                user_chat_id=chat.id,
                sender_id=current_id,
                sender_type=sender_type_eff,
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
                    "sender_type": sender_type_eff,
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

                # Notification payload
                notif_payload = {
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
                    "to_salon_id": receiver_id if receiver_type == "salon" else None,
                    "sender_id": current_id,
                    "sender_type": sender_type_eff,
                    "chat_id": str(chat.id),
                    "unread_count": unread_count,
                    "time": _now_local_iso(),
                }

                # Broadcast a lightweight notification event to the room
                await manager.broadcast(room_id, notif_payload)

                # ── Agar user salon ga yozsa, salon-level room ga ham broadcast ──
                if receiver_type == "salon":
                    salon_room_id = f"salon_{receiver_id}"
                    await manager.broadcast(salon_room_id, notif_payload)

                # ── Agar user employeega yozsa, employee salon room ga ham xabar ──
                if receiver_type == "employee":
                    try:
                        emp = db.query(Employee).filter(Employee.id == receiver_id).first()
                        if emp and getattr(emp, "salon_id", None):
                            emp_salon_room_id = f"salon_{emp.salon_id}"
                            await manager.broadcast(emp_salon_room_id, notif_payload)
                    except Exception:
                        pass

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