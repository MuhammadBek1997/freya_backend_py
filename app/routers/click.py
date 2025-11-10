from dataclasses import Field
import json
import logging
from typing import Dict, List, Literal, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user, get_current_user_only
from app.config import settings

from app.database import get_db
from app.models.employee import Employee
from app.models.payment import ClickPayment
from app.models.payment_card import PaymentCard
from app.models.user import User
from app.schemas.Click import (
    CardTokenCreate,
    CardTokenVerify,
    PaymentCard as PaymentCardSchema,
)
from app.services.Click import PaymentStatus
from app.services.click_complate import complate_payment
from app.utils.payment_validator import PaymentValidator


router = APIRouter(
    prefix="/click",
    tags=["Click"],
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
        # Agar karta mavjud bo'lib, tasdiqlanmagan bo'lsa — qayta token olish
        if not get_card.is_verified:
            result = settings.click_provider.create_card_token(
                card_number=data.card_number,
                expire_date=data.expire_date,
                temporary=0,
            )
            if result.get("error_code"):
                return {
                    "success": False,
                    "error_code": result["error_code"],
                    "error": result.get("error_note"),
                }

            # Mavjud yozuvni yangilaymiz va tasdiqlashni kutamiz
            get_card.card_token = result["card_token"]
            get_card.expiry_at = data.expire_date
            get_card.is_active = False
            get_card.is_verified = False
            db.add(get_card)
            db.commit()
            db.refresh(get_card)

            return {
                "success": True,
                "card_id": get_card.id,
                "message": "sms_code_sent",
            }

        # Aks holda, karta tasdiqlangan — xatolik qaytaramiz
        return {
            "success": False,
            "error_code": "CARD_ALREADY_EXISTS",
            "error": "Ushbu karta allaqachon mavjud.",
        }

    result = settings.click_provider.create_card_token(
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

    result = settings.click_provider.verify_card_token(
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


@router.delete("/card/{card_id}")
def delete_card_token(
    card_id: str,
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
):
    """
    Foydalanuvchi kartasining tokenini Click provayderidan o'chirib,
    bazadagi kartani ham o'chirish.
    """

    card = (
        db.query(PaymentCard)
        .filter(PaymentCard.id == card_id, PaymentCard.user_id == current_user.id)
        .first()
    )

    if not card:
        return {
            "success": False,
            "error_code": "CARD_NOT_FOUND",
            "error": "Ushbu karta mavjud emas.",
        }

    # Agar karta tasdiqlanmagan bo'lsa — faqat bazadan o'chiramiz
    if not card.is_verified:
        if getattr(current_user, "card_for_auto_pay", None) == card_id:
            current_user.card_for_auto_pay = None
            current_user.auto_pay_for_premium = False
            db.add(current_user)

        was_default = card.is_default
        db.delete(card)
        if was_default:
            remaining = (
                db.query(PaymentCard)
                .filter(PaymentCard.user_id == current_user.id)
                .order_by(PaymentCard.created_at.desc())
                .first()
            )
            if remaining:
                remaining.is_default = True
                db.add(remaining)
        db.commit()
        return {"success": True}

    # Tasdiqlangan karta — provayderdan tokenni o'chiramiz
    result = settings.click_provider.delete_card_token(card_token=card.card_token)
    if result.get("error_code"):
        return {
            "success": False,
            "error_code": result.get("error_code"),
            "error": result.get("error_note", "Token o'chirishda xatolik"),
        }

    # Agar auto-pay ushbu karta bilan bog'langan bo'lsa, uni o'chiramiz
    if getattr(current_user, "card_for_auto_pay", None) == card_id:
        current_user.card_for_auto_pay = None
        current_user.auto_pay_for_premium = False
        db.add(current_user)

    was_default = card.is_default

    # Kartani bazadan o'chirish
    db.delete(card)

    # Agar default karta o'chirilsa, qolganlardan birini default qilamiz
    if was_default:
        remaining = (
            db.query(PaymentCard)
            .filter(PaymentCard.user_id == current_user.id)
            .order_by(PaymentCard.created_at.desc())
            .first()
        )
        if remaining:
            remaining.is_default = True
            db.add(remaining)

    db.commit()

    return {"success": True}


@router.post("/pay/premium")
def pay_for_premium(
    card_id: str = None,
    quantity_months: int = 1,
    current_user: User = Depends(get_current_user_only),
    db: Session = Depends(get_db),
):
    amount_for_month = settings.AMOUNT_FOR_PREMIUM  # Example amount for 1 month
    payment = ClickPayment(
        payment_for=f"premium_{current_user.id}_{quantity_months}",
        amount=str(amount_for_month * quantity_months),  # Example amount
        status="created",
        payment_card_id=card_id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if card_id:
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
        if not get_card:
            return {
                "success": False,
                "error_code": "CARD_NOT_FOUND_OR_INACTIVE",
                "error": "Karta topilmadi yoki faol emas.",
            }

        payment.status = PaymentStatus.PENDING.value
        db.commit()
        result = settings.click_provider.payment_with_token(
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
        invoice = settings.click_provider.create_invoice(
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


@router.post("/pay/for_post/{pay_with}")
def pay_for_post(
    post_quantity: int,
    pay_with: Literal["redirect", "invoice"],
    card_type: Literal["humo", "uzcard"] = Query(
        "humo", description="Type of card (Humo or Uzcard) *if pay with redirect"
    ),
    return_url: str = Query(
        settings.frontend_url, description="URL to return after payment *if pay with redirect",
    ),
    employe: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if employe.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Faqat ishchi huquqi bilan kirish mumkin",
        )

    if pay_with not in ["redirect", "invoice"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Noto'g'ri to'lov usuli"
        )

    amount_per_post = settings.AMOUNT_FOR_PER_POST  # Example amount for 1 post
    total_amount = amount_per_post * post_quantity
    payment = ClickPayment(
        payment_for=f"post_{employe.id}_{post_quantity}",
        amount=str(total_amount),  # Example amount
        status="created",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if pay_with == "invoice":
        invoice = settings.click_provider.create_invoice(
            amount=payment.amount,
            phone_number=employe.phone,
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
    else:
        if card_type not in ["humo", "uzcard"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Noto'g'ri karta turi",
            )

        return {
            "success": True,
            "payment_id": payment.id,
            "redirect_url": f"https://my.click.uz/services/pay?service_id={settings.click_provider.merchant_service_id}&merchant_id={settings.click_provider.merchant_id}&amount={payment.amount}&transaction_param={payment.id}&return_url={return_url}&card_type={card_type}",
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

    validation_result = settings.click_provider.validate_webhook_data(
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

    validation_result = settings.click_provider.validate_webhook_data(
        webhook_data=data, expected_amount=payment.amount, payment_status=payment.status
    )

    if validation_result["error"] == "0":
        # Обновить статус на CONFIRMED
        payment.status = PaymentStatus.CONFIRMED.value
        db.commit()
        complate_payment(payment, db)
        if payment.payment_for.startswith("premium"):
            user_id = payment.payment_for.split("_")[1]
            c_user = db.query(User).filter(User.id == user_id).first()
            c_user.auto_pay_for_premium = True
            c_user.card_for_auto_pay = payment.payment_card_id
            db.commit()
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
