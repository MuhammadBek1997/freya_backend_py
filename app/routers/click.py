from fastapi import APIRouter, Depends
from app.config import settings

import hashlib
import hmac
import time
import httpx


router = APIRouter(
    prefix="/click",
    tags=["Click"],
)


class ClickAPI:
    BASE_URL = "https://api.click.uz/v2/merchant"  # тест/боевой API зависит от среды

    def __init__(self, service_id: int, merchant_id: str, secret_key: str):
        self.service_id = service_id
        self.merchant_id = merchant_id
        self.secret_key = secret_key

    def _generate_sign(self, data: dict) -> str:
        """
        Генерация подписи SHA-256 для Click API
        """
        sorted_items = sorted(data.items())
        payload = "".join(str(v) for _, v in sorted_items)
        sign = hmac.new(
            self.secret_key.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return sign

    async def create_invoice(self, amount: float, order_id: str, return_url: str):
        """
        Создает инвойс для оплаты через Click
        """
        data = {
            "service_id": self.service_id,
            "merchant_id": self.merchant_id,
            "amount": amount,
            "transaction_param": order_id,
            "return_url": return_url,
        }

        data["sign_string"] = self._generate_sign(data)

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.BASE_URL}/invoice/create/", json=data)
            return response.json()

    async def check_payment(self, invoice_id: str):
        """
        Проверка статуса платежа
        """
        data = {
            "merchant_id": self.merchant_id,
            "invoice_id": invoice_id,
        }

        data["sign_string"] = self._generate_sign(data)

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.BASE_URL}/invoice/status/", json=data)
            return response.json()

click = ClickAPI(
    service_id=settings.click_service_id,
    merchant_id=settings.click_merchant_id,
    secret_key=settings.click_secret_key,
)
@router.post("/prepare_payment")
async def prepare_payment(
    payment_data: dict,
):
    print(payment_data)
    """Prepare a payment using Click service."""
    return {}


@router.post("/complete_payment")
async def complete_payment(
    payment_data: dict,
):
    print(payment_data)
    """Complete a payment using Click service."""
    return {}


@router.port("/create_payment")
async def create_payment():
    """Create a payment using Click service."""
    invoice = await click.create_invoice(
        amount=10000.00,
        order_id="ORDER12345",
        return_url=f"{settings.frontend_url}/payment/callback",
    )
    return invoice
