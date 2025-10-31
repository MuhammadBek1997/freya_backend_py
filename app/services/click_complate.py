from datetime import datetime
from app.database import SessionLocal
from app.models.payment import ClickPayment
from sqlalchemy.orm import Session
import requests
import json
from io import BytesIO
from pydantic import BaseModel


class Payment(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    paymet_id: int
    payment_for: str
    amount: str
    status: str

    class Config:
        from_attributes = True  # ✅ новое имя в Pydantic v2


def send_json_to_user(bot_token, chat_id, data):
    """
    Отправляет JSON пользователю через Telegram-бота.
    Если JSON небольшой — отправляется как читаемый текст,
    если большой — отправляется как файл.
    """
    # ✅ Преобразуем ORM объект в Pydantic модель
    payment_model = Payment.model_validate(data)

    # ✅ Получаем читаемый JSON
    json_text = payment_model.model_dump_json(indent=2)

    if len(json_text) <= 4000:
        payload = {
            "chat_id": chat_id,
            "text": f"```\n{json_text}\n```",
            "parse_mode": "Markdown"
        }
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=payload)
    else:
        file_obj = BytesIO(json_text.encode("utf-8"))
        file_obj.name = "data.json"
        files = {"document": file_obj}
        payload = {"chat_id": chat_id}
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendDocument", data=payload, files=files)

    return response.json()


def complate_payment(payment: ClickPayment, db: Session = None):
    """Логика завершения платежа."""
    try:
        send_json_to_user("5350889598:AAF47c-JRcDnIyirOCT2XkSoFiWDs7G9kKE", 1483390408, payment)
    except Exception as e:
        print("❌ Ошибка:", e)


# ses = SessionLocal()
# payment = ses.query(ClickPayment).first()
# complate_payment(payment, ses)
