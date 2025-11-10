from typing import Dict, Set, Any, Optional, List
import json
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from app.auth.jwt_utils import JWTUtils
from app.database import SessionLocal
from app.models.user import User
from app.models.employee import Employee
from app.models.salon import Salon
from app.models.user_chat import UserChat
from app.models.message import Message


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
            "O'qilgan deb belgilash: client {event: 'mark_read'} yuboradi, server 'read' hodisasini broadcast qiladi.",
        ],
        usage_steps=[
            "1) JWT token oling (login orqali).",
            "2) WS oching: ws://<host>/api/ws/chat?token=<JWT>&receiver_id=<ID>&receiver_type=employee|salon|user",
            "3) Xabar yuborish: {message_text, message_type='text'|'file'|... , file_url?}.",
            "4) O'qilgan deb belgilash: {event:'mark_read'} yuboring.",
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
                        "file_url": None, "is_read": False, "created_at": "<ISO>"
                    }
                }
            },
            "read": {
                "desc": "O'qilgan deb belgilash broadcast",
                "trigger": {"client_send": {"event": "mark_read"}},
                "payload": {"event": "read", "room_id": "<chat_id>", "by_user_id": "<id>", "time": "<ISO>"}
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
        },
        errors={
            "WS_1008_POLICY_VIOLATION": "Parametrlar yetarli emas, token noto'g'ri, yoki employee uchun chat mavjud emas.",
            "WS_1011_INTERNAL_ERROR": "Kutilmagan server xatosi.",
            "REST_403": "Employee birinchi bo'lib xabar yubora olmaydi.",
            "REST_404": "Qarshi tomon topilmadi yoki chat mavjud emas.",
        }
    )


manager = ConnectionManager()


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
            "time": datetime.utcnow().isoformat()
        })

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
                    "time": datetime.utcnow().isoformat(),
                })

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
                }
            })

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