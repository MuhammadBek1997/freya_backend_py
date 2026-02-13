# Chat WebSocket — Ulanish Qo'llanmasi

## Endpoint

```
wss://<host>/api/ws/chat
```

---

## Query parametrlar

| Parametr | Talab | Tavsif |
|---|---|---|
| `token` | Majburiy | JWT access token |
| `receiver_type` | Majburiy | `user` \| `employee` \| `salon` |
| `receiver_id` | `receiver_type=salon` da ixtiyoriy | Qarshi tomon ID |

---

## Ulanish turlari

### 1. Mobil foydalanuvchi → Salon ga yozadi
```
wss://host/api/ws/chat?token=<USER_JWT>&receiver_type=salon&receiver_id=<SALON_ID>
```
- Chat room avtomatik yaratiladi (birinchi marta yozilganda)
- Shu salon'ning admin'lariga real-time notification ketadi

### 2. Mobil foydalanuvchi → Xodim (Employee) ga yozadi
```
wss://host/api/ws/chat?token=<USER_JWT>&receiver_type=employee&receiver_id=<EMPLOYEE_ID>
```
- Chat room avtomatik yaratiladi

### 3. Admin → Bitta foydalanuvchi bilan chat
```
wss://host/api/ws/chat?token=<ADMIN_JWT>&receiver_type=user&receiver_id=<USER_ID>
```
- Chat room mavjud bo'lmasa avtomatik yaratiladi
- Admin o'z salon'iga tegishli userlar bilan chat ochadi

### 4. Admin → Barcha xabarlarni eshitish (GLOBAL NOTIFICATION)
```
wss://host/api/ws/chat?token=<ADMIN_JWT>&receiver_type=salon
```
- `receiver_id` shart emas
- Admin shu ulanish orqali salon'ga kelgan BARCHA yangi xabarlardan notification oladi
- Admin panel sahifasi ochilganda avtomatik ulanishi tavsiya etiladi

### 5. Xodim (Employee) → Foydalanuvchiga javob beradi
```
wss://host/api/ws/chat?token=<EMP_JWT>&receiver_type=user&receiver_id=<USER_ID>
```
- Faqat mavjud chat'ga ulanadi (foydalanuvchi avval yozgan bo'lishi kerak)

---

## Xabar yuborish

```json
{
  "message_text": "Salom!",
  "message_type": "text"
}
```

Fayl yuborish uchun:
```json
{
  "message_text": null,
  "message_type": "image",
  "file_url": "https://cdn.example.com/image.jpg"
}
```

---

## Serverdan keladigan eventlar

### `history` — Ulanishda oxirgi 50 xabar
```json
{
  "event": "history",
  "room_id": "<chat_id>",
  "items": [
    {
      "id": "uuid",
      "sender_id": "uuid",
      "sender_type": "user | employee | salon",
      "receiver_id": "uuid",
      "receiver_type": "user | employee | salon",
      "message_text": "Salom!",
      "message_type": "text",
      "file_url": null,
      "is_read": false,
      "created_at": "2024-01-01T10:00:00",
      "created_at_local": "2024-01-01T15:00:00+05:00"
    }
  ],
  "pagination": { "limit": 50, "offset": 0, "total": 123 }
}
```

### `message` — Yangi xabar keldi
```json
{
  "event": "message",
  "room_id": "<chat_id>",
  "message": {
    "id": "uuid",
    "sender_id": "uuid",
    "sender_type": "user",
    "receiver_id": "uuid",
    "receiver_type": "salon",
    "message_text": "Salom!",
    "message_type": "text",
    "file_url": null,
    "is_read": false,
    "created_at_local": "2024-01-01T15:00:00+05:00"
  }
}
```

### `notification` — Real-time bildirishnoma
```json
{
  "event": "notification",
  "room_id": "<chat_id>",
  "kind": "chat_message",
  "receiver_type": "salon",
  "to_user_id": null,
  "to_employee_id": null,
  "to_salon_id": "<salon_id>",
  "sender_id": "<user_id>",
  "sender_type": "user",
  "chat_id": "<chat_id>",
  "message": "Salom!",
  "unread_count": 3,
  "time": "2024-01-01T15:00:00+05:00",
  "title": "Yangi xabar",
  "title_ru": "Новое сообщение",
  "title_en": "New message"
}
```

### `read` — Xabarlar o'qildi
```json
{
  "event": "read",
  "room_id": "<chat_id>",
  "by_user_id": "<id>",
  "time": "2024-01-01T15:00:00+05:00"
}
```

### `join` — Room'ga ulanildi
```json
{
  "event": "join",
  "room_id": "<chat_id>",
  "user_id": "<id>",
  "role": "user | employee | admin",
  "time": "2024-01-01T15:00:00+05:00"
}
```

---

## Xabarlarni o'qilgan deb belgilash

```json
{ "event": "mark_read" }
```

---

## Tarix (pagination)

```json
{ "event": "history", "limit": 50, "offset": 50 }
```

---

## Mobil dastur uchun flow

```
1. Foydalanuvchi salonni tanlaydi
2. WS ochadi: receiver_type=salon, receiver_id=<salon_id>
3. Chat room yo'q bo'lsa — backend avtomatik yaratadi
4. history event keladi — oxirgi xabarlar ko'rinadi
5. Foydalanuvchi yozadi — message event broadcast bo'ladi
6. Admin salon WS'da notification oladi — conversations yangilanadi
7. Admin shu userga click qiladi — receiver_type=user, receiver_id=<user_id> bilan ulanadi
8. Ikkala tomon bir xil room_id da bo'ladi — real-time ishlaydi
```

---

## REST API (WS ishlamaganda fallback)

| Method | Endpoint | Kim uchun |
|---|---|---|
| POST | `/api/messages/send` | Foydalanuvchi xabar yuboradi |
| POST | `/api/messages/employee/send` | Xodim javob beradi |
| POST | `/api/messages/admin/send` | Admin javob beradi |
| GET | `/api/messages/admin/conversations` | Admin suhbatlar ro'yxati |
| GET | `/api/messages/admin/conversation/{user_id}` | Admin bitta suhbat |

---

## Xatolar

| Kod | Sabab |
|---|---|
| 1008 | Token noto'g'ri / parametr yetishmayapti |
| 1011 | Server ichki xatosi |

---

## Muhit URL

```
Production: wss://freya-2aff07996d13.herokuapp.com/api/ws/chat
```
