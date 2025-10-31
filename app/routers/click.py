import json
import logging
from typing import Dict, List, Union
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user, get_current_user_only
from app.config import settings

import hashlib
import hmac
import time
import httpx

from app.database import get_db
from app.models.payment import ClickPayment
from app.models.payment_card import PaymentCard
from app.models.user import User
from app.schemas.Click import (
    CardTokenCreate,
    CardTokenVerify,
    PaymentCard as PaymentCardSchema,
)
from app.services.Click import ClickPaymentProvider, PaymentStatus
from app.services.click_complate import complate_payment
from app.utils.payment_validator import PaymentValidator


router = APIRouter(
    prefix="/click",
    tags=["Click"],
)

click_provider = ClickPaymentProvider(
    merchant_id="44558",
    merchant_service_id="80178",
    merchant_user_id="61876",
    secret_key="j4qMFKcdBIYS",
)

cards_temp = {}


@router.post("/card/create")
def create_card_token(
    data: CardTokenCreate,
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
):
    get_card = (
        db.query(PaymentCard)
        .filter(
            PaymentCard.user_id == current_user.id,
            PaymentCard.card_number == data.card_number,
        )
        .first()
    )
    if get_card:
        return {
            "success": False,
            "error_code": "CARD_ALREADY_EXISTS",
            "error": "Ushbu karta allaqachon mavjud.",
        }

    result = click_provider.create_card_token(
        card_number=data.card_number,
        expire_date=data.expire_date,
        temporary=0,
    )
    if result.get("error_code"):
        return {
            "success": False,
            "error_code": result["error_code"],
            "error": result["error_note"],
        }

    db_card = PaymentCard(
        user_id=current_user.id,
        card_token=result["card_token"],
        card_number=data.card_number,
        expiry_at=data.expire_date,
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)

    return {
        "success": True,
        "card_id": db_card.id,
        "message": "sms_code_sent",
    }


@router.post("/card/verify")
def verify_card_token(
    data: CardTokenVerify,
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
):
    get_card = (
        db.query(PaymentCard)
        .filter(
            PaymentCard.id == data.card_id,
            PaymentCard.user_id == current_user.id,
        )
        .first()
    )
    if not get_card:
        return {
            "success": False,
            "error_code": "CARD_NOT_FOUND",
            "error": "Ushbu karta mavjud emas.",
        }

    result = click_provider.verify_card_token(
        card_token=get_card.card_token, sms_code=data.sms_code
    )
    if result.get("error_code"):
        return {
            "success": False,
            "error_code": result["error_code"],
            "error": result["error_note"],
        }

    get_card.is_verified = True
    get_card.is_active = True
    db.add(get_card)
    db.commit()

    return {
        "success": True,
    }


@router.get("/cards", response_model=List[Union[PaymentCardSchema, Dict, None]])
def get_user_payment_cards(
    current_user: User = Depends(get_current_user_only), db: Session = Depends(get_db)
):
    cards = db.query(PaymentCard).filter(PaymentCard.user_id == current_user.id).all()
    masked_cards = []
    for card in cards:
        masked_cards.append(
            PaymentCardSchema(
                id=card.id,
                card_number=PaymentValidator.mask_card_number(card.card_number),
                expiry_at=(
                    card.expiry_at[:2] + "/" + card.expiry_at[2:]
                    if card.expiry_at
                    else card.expiry_at
                ),
                is_default=card.is_default,
                is_active=card.is_active,
            )
        )
    return masked_cards


@router.post("/pay/premium")
def pay_for_premium(
    card_id: str = None,
    quantity_months: int = 1,
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
):
    amount_for_month = 1000  # Example amount for 1 month
    payment = ClickPayment(
        payment_for=f"premium_{current_user.id}",
        amount=str(amount_for_month * quantity_months),  # Example amount
        status="created",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if card_id:
        print(card_id)
        print(current_user.id)
        get_card = (
            db.query(PaymentCard)
            .where(
                PaymentCard.id == card_id,
                PaymentCard.user_id == current_user.id,
                PaymentCard.is_active == True,
                PaymentCard.is_verified == True,
            )
            .first()
        )
        print(get_card)
        if not get_card:
            return {
                "success": False,
                "error_code": "CARD_NOT_FOUND_OR_INACTIVE",
                "error": "Karta topilmadi yoki faol emas.",
            }

        payment.status = PaymentStatus.PENDING.value
        db.commit()
        result = click_provider.payment_with_token(
            card_token=get_card.card_token,
            amount=payment.amount,
            merchant_trans_id=payment.id,
        )
        if result.get("error_code"):
            payment.status = PaymentStatus.ERROR.value
            db.commit()
            return {
                "success": False,
                "error_code": result["error_code"],
                "error": result["error_note"],
            }
        
        return {
            "success": True,
            "payment_id": payment.id,
        }
    else:
        invoice = click_provider.create_invoice(
            amount=payment.amount,
            phone_number=current_user.phone,
            merchant_trans_id=payment.id,
        )

        if invoice.get("error_code"):
            payment.status = PaymentStatus.ERROR.value
            db.commit()
            return {
                "success": False,
                "error_code": invoice["error_code"],
                "error": invoice["error_note"],
            }

        return {
            "success": True,
            "message": "invoice_created",
            "invoice_id": invoice["invoice_id"],
        }

# ============= WEBHOOK ENDPOINTS =============
def parse_webhook_body(body: bytes) -> Dict[str, str]:
    """
    Парсинг тела webhook запроса от Click

    Args:
        body: Сырое тело запроса (bytes)

    Returns:
        Dict с распарсенными данными

    Example:
        body = b'click_trans_id=123&service_id=456&amount=1000'
        data = parse_webhook_body(body)
        # {'click_trans_id': '123', 'service_id': '456', 'amount': '1000'}
    """
    from urllib.parse import parse_qs, unquote

    try:
        # Декодируем bytes в строку
        body_str = body.decode("utf-8")
        logging.debug(f"Raw webhook body: {body_str}")

        # Парсим URL-encoded данные
        parsed = parse_qs(body_str, keep_blank_values=True)

        # Конвертируем списки в строки (parse_qs возвращает списки)
        result = {key: values[0] if values else "" for key, values in parsed.items()}

        logging.info(
            f"📥 Webhook data parsed: {json.dumps(result, ensure_ascii=False)}"
        )
        return result

    except Exception as e:
        logging.error(f"❌ Failed to parse webhook body: {e}")
        return {}


@router.post("/webhook/prepare")
async def webhook_prepare(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    data = parse_webhook_body(body)

    # Получить payment из БД
    payment = (
        db.query(ClickPayment)
        .filter(ClickPayment.id == data["merchant_trans_id"])
        .first()
    )
    if not payment:
        return {
            "error": "5",
            "error_note": "Payment not found",
        }

    validation_result = click_provider.validate_webhook_data(
        webhook_data=data,
        expected_amount=payment.amount,
        payment_status=payment.status,
    )

    if validation_result["error"] == "0":
        payment.status = PaymentStatus.WAITING.value
        db.commit()

    response = {
        **validation_result,
        "click_trans_id": data.get("click_trans_id"),
        "merchant_trans_id": data.get("merchant_trans_id"),
        "merchant_prepare_id": payment.paymet_id,
    }
    print(response)

    return response


@router.post("/webhook/complete")
async def webhook_complete(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    data = parse_webhook_body(body)

    # Получить payment из БД
    payment = (
        db.query(ClickPayment)
        .filter(ClickPayment.paymet_id == data["merchant_prepare_id"])
        .first()
    )

    validation_result = click_provider.validate_webhook_data(
        webhook_data=data, expected_amount=payment.amount, payment_status=payment.status
    )

    if validation_result["error"] == "0":
        # Обновить статус на CONFIRMED
        payment.status = PaymentStatus.CONFIRMED.value
        db.commit()
        complate_payment(payment, db)
    elif int(data.get("error", 0)) < 0:
        payment.status = PaymentStatus.REJECTED.value
        db.commit()
        # Обновить статус на REJECTED

    response = {
        **validation_result,
        "click_trans_id": data.get("click_trans_id"),
        "merchant_trans_id": data.get("merchant_trans_id"),
        "merchant_prepare_id": data.get("merchant_prepare_id"),
        "merchant_confirm_id": data.get("merchant_prepare_id"),
    }
    print(response)

    return response
