import hashlib
import httpx
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Payment, Employee, User, Salon, SalonTopHistory
from app.config import settings


class ClickService:
    def __init__(self):
        self.merchant_id = settings.click_merchant_id
        self.service_id = settings.click_service_id
        self.secret_key = settings.click_secret_key
        self.merchant_user_id = settings.click_merchant_user_id
        self.base_url = settings.click_api_url or "https://api.click.uz/v2"

    def generate_signature(self, params: Dict[str, Any]) -> str:
        """MD5 hash yaratish"""
        sorted_params = "&".join([f"{key}={params[key]}" for key in sorted(params.keys())])
        signature_string = sorted_params + self.secret_key
        return hashlib.md5(signature_string.encode()).hexdigest()

    async def create_payment_url(self, payment_data: Dict[str, Any]) -> str:
        """To'lov URL yaratish"""
        amount = payment_data.get("amount")
        order_id = payment_data.get("order_id")
        return_url = payment_data.get("return_url", f"{settings.frontend_url}/payment/success")
        description = payment_data.get("description", "To'lov")

        params = {
            "merchant_id": self.merchant_id,
            "service_id": self.service_id,
            "amount": amount,
            "transaction_param": order_id,
            "return_url": return_url,
            "description": description
        }

        signature = self.generate_signature(params)
        params["sign"] = signature

        query_string = "&".join([f"{key}={params[key]}" for key in params.keys()])
        return f"{self.base_url}/payments/create?{query_string}"

    async def create_employee_post_payment(self, employee_id: str, post_count: int = 4, db: Session = None) -> Dict[str, Any]:
        """Employee post uchun to'lov"""
        try:
            if db is None:
                db = next(get_db())

            amount = post_count * 5000  # Har bir post uchun 5000 so'm
            order_id = f"emp_post_{employee_id}_{int(datetime.now().timestamp())}"

            # Payment record yaratish
            payment = Payment(
                employee_id=employee_id,
                amount=amount,
                payment_type="employee_post",
                transaction_id=order_id,
                description=f"{post_count} ta post uchun to'lov",
                status="pending"
            )
            db.add(payment)
            db.commit()
            db.refresh(payment)

            # Click URL yaratish
            payment_url = await self.create_payment_url({
                "amount": amount,
                "order_id": order_id,
                "description": f"{post_count} ta post uchun to'lov"
            })

            return {
                "success": True,
                "payment_id": payment.id,
                "payment_url": payment_url,
                "amount": amount,
                "order_id": order_id
            }
        except Exception as error:
            print(f"Employee post payment error: {error}")
            return {"success": False, "error": str(error)}

    async def create_user_premium_payment(self, user_id: str, duration: int = 30, db: Session = None) -> Dict[str, Any]:
        """User premium uchun to'lov"""
        try:
            if db is None:
                db = next(get_db())

            amount = 50000 if duration == 30 else 150000  # 30 kun - 50k, 90 kun - 150k
            order_id = f"user_premium_{user_id}_{int(datetime.now().timestamp())}"

            # Payment record yaratish
            payment = Payment(
                user_id=user_id,
                amount=amount,
                payment_type="user_premium",
                transaction_id=order_id,
                description=f"{duration} kunlik premium obuna",
                status="pending"
            )
            db.add(payment)
            db.commit()
            db.refresh(payment)

            # Click URL yaratish
            payment_url = await self.create_payment_url({
                "amount": amount,
                "order_id": order_id,
                "description": f"{duration} kunlik premium obuna"
            })

            return {
                "success": True,
                "payment_id": payment.id,
                "payment_url": payment_url,
                "amount": amount,
                "order_id": order_id,
                "duration": duration
            }
        except Exception as error:
            print(f"User premium payment error: {error}")
            return {"success": False, "error": str(error)}

    async def create_salon_top_payment(self, salon_id: str, admin_id: str, duration: int = 7, db: Session = None) -> Dict[str, Any]:
        """Salon top uchun to'lov"""
        try:
            if db is None:
                db = next(get_db())

            amount = 100000 if duration == 7 else 300000  # 7 kun - 100k, 30 kun - 300k
            order_id = f"salon_top_{salon_id}_{int(datetime.now().timestamp())}"

            # Payment record yaratish
            payment = Payment(
                salon_id=salon_id,
                amount=amount,
                payment_type="salon_top",
                transaction_id=order_id,
                description=f"{duration} kunlik salon top",
                status="pending"
            )
            db.add(payment)
            db.commit()
            db.refresh(payment)

            # Click URL yaratish
            payment_url = await self.create_payment_url({
                "amount": amount,
                "order_id": order_id,
                "description": f"{duration} kunlik salon top"
            })

            return {
                "success": True,
                "payment_id": payment.id,
                "payment_url": payment_url,
                "amount": amount,
                "order_id": order_id,
                "duration": duration
            }
        except Exception as error:
            print(f"Salon top payment error: {error}")
            return {"success": False, "error": str(error)}

    async def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """To'lov holatini tekshirish"""
        try:
            params = {
                "merchant_id": self.merchant_id,
                "service_id": self.service_id,
                "transaction_param": transaction_id
            }

            signature = self.generate_signature(params)
            params["sign"] = signature

            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/payments/status", params=params)
                return response.json()
        except Exception as error:
            print(f"Payment status check error: {error}")
            return {"success": False, "error": str(error)}

    async def handle_successful_payment(self, transaction_id: str, click_trans_id: str, db: Session = None) -> Dict[str, Any]:
        """To'lov muvaffaqiyatli bo'lganda"""
        try:
            if db is None:
                db = next(get_db())

            # Payment statusini yangilash
            payment = db.query(Payment).filter(Payment.transaction_id == transaction_id).first()
            if not payment:
                raise Exception("Payment not found")

            # Idempotency: allaqachon yakunlangan bo'lsa qaytish
            if payment.status == "completed":
                return {"success": True, "payment": payment}

            # Duplicate click_trans_id tekshirish
            if click_trans_id:
                duplicate = (
                    db.query(Payment)
                    .filter(Payment.click_trans_id == click_trans_id, Payment.transaction_id != transaction_id)
                    .first()
                )
                if duplicate:
                    raise Exception("Duplicate click_trans_id")

            payment.status = "completed"
            payment.click_trans_id = click_trans_id
            payment.updated_at = datetime.utcnow()
            db.commit()

            # Payment turiga qarab tegishli amallarni bajarish
            if payment.payment_type == "employee_post":
                await self.handle_employee_post_payment(payment, db)
            elif payment.payment_type == "user_premium":
                await self.handle_user_premium_payment(payment, db)
            elif payment.payment_type == "salon_top":
                await self.handle_salon_top_payment(payment, db)

            return {"success": True, "payment": payment}
        except Exception as error:
            print(f"Handle successful payment error: {error}")
            return {"success": False, "error": str(error)}

    async def handle_employee_post_payment(self, payment: Payment, db: Session):
        """Employee post to'lovi muvaffaqiyatli bo'lganda"""
        post_count = payment.amount // 5000
        
        # Employee post limitini yangilash
        employee = db.query(Employee).filter(Employee.id == payment.employee_id).first()
        if employee:
            # Bu yerda employee post limit logikasini qo'shish kerak
            pass

    async def handle_user_premium_payment(self, payment: Payment, db: Session):
        """User premium to'lovi muvaffaqiyatli bo'lganda"""
        duration = 30 if payment.amount == 50000 else 90
        end_date = datetime.utcnow() + timedelta(days=duration)

        # User premium statusini yangilash
        user = db.query(User).filter(User.id == payment.user_id).first()
        if user:
            # Bu yerda user premium logikasini qo'shish kerak
            pass

    async def handle_salon_top_payment(self, payment: Payment, db: Session):
        """Salon top to'lovi muvaffaqiyatli bo'lganda"""
        duration = 7 if payment.amount == 100000 else 30
        end_date = datetime.utcnow() + timedelta(days=duration)

        # Salon top qilish
        salon = db.query(Salon).filter(Salon.id == payment.salon_id).first()
        if salon:
            salon.is_top = True
            db.commit()

        # Top history qo'shish
        salon_top_history = SalonTopHistory(
            salon_id=payment.salon_id,
            end_date=end_date,
            is_active=True
        )
        db.add(salon_top_history)
        db.commit()

    def _generate_auth_header(self) -> str:
        """Click API uchun Auth header yaratish"""
        timestamp = str(int(time.time()))
        digest = hashlib.sha1((timestamp + self.secret_key).encode()).hexdigest()
        return f"{self.merchant_user_id}:{digest}:{timestamp}"

    async def create_card_token(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """Karta tokenini yaratish"""
        try:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Auth": self._generate_auth_header()
            }

            payload = {
                "service_id": self.service_id,
                "card_number": card_data["card_number"],
                "expire_date": f"{card_data['expiry_month']:02d}{card_data['expiry_year']}",
                "temporary": card_data.get("temporary", True)
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/merchant/card_token/request",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "card_token": result.get("card_token"),
                        "phone_number": result.get("phone_number"),
                        "temporary": result.get("temporary", True),
                        "error_code": result.get("error_code", 0),
                        "error_note": result.get("error_note")
                    }
                else:
                    return {
                        "success": False,
                        "error_code": response.status_code,
                        "error_note": f"HTTP Error: {response.status_code}"
                    }

        except Exception as e:
            return {
                "success": False,
                "error_code": -1,
                "error_note": f"Token yaratishda xatolik: {str(e)}"
            }

    async def verify_card_token(self, card_token: str, sms_code: str) -> Dict[str, Any]:
        """Karta tokenini tasdiqlash (SMS kod bilan)"""
        try:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Auth": self._generate_auth_header()
            }

            payload = {
                "service_id": self.service_id,
                "card_token": card_token,
                "sms_code": sms_code
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/merchant/card_token/verify",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "verified": result.get("error_code", 0) == 0,
                        "error_code": result.get("error_code", 0),
                        "error_note": result.get("error_note")
                    }
                else:
                    return {
                        "success": False,
                        "error_code": response.status_code,
                        "error_note": f"HTTP Error: {response.status_code}"
                    }

        except Exception as e:
            return {
                "success": False,
                "error_code": -1,
                "error_note": f"Token tasdiqlashda xatolik: {str(e)}"
            }

    async def create_direct_card_payment(self, payment_data: Dict[str, Any], db: Session = None) -> Dict[str, Any]:
        """To'g'ridan-to'g'ri karta bilan to'lov"""
        try:
            if db is None:
                db = next(get_db())

            # To'lov yaratish
            transaction_id = f"direct_{int(datetime.now().timestamp())}"
            
            payment = Payment(
                transaction_id=transaction_id,
                amount=payment_data["amount"],
                payment_type=payment_data["payment_type"],
                status="pending",
                user_id=payment_data.get("user_id"),
                employee_id=payment_data.get("employee_id"),
                salon_id=payment_data.get("salon_id"),
                description=f"Direct card payment - {payment_data['payment_type']}"
            )
            
            db.add(payment)
            db.commit()
            db.refresh(payment)

            # Click API ga to'lov so'rovi
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Auth": self._generate_auth_header()
            }

            payload = {
                "service_id": self.service_id,
                "card_token": payment_data["card_token"],
                "amount": payment_data["amount"],
                "transaction_parameter": transaction_id
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/merchant/card_token/payment",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    
                    # Payment modelini yangilash
                    payment.click_trans_id = str(result.get("payment_id", ""))
                    payment.status = "processing" if result.get("error_code", 0) == 0 else "failed"
                    db.commit()

                    # Muvaffaqiyatli to'lov bo'lsa, handle qilish
                    if result.get("error_code", 0) == 0 and result.get("payment_status") == 2:
                        await self.handle_successful_payment(transaction_id, str(result.get("payment_id")), db)
                        payment.status = "completed"
                        db.commit()

                    return {
                        "success": True,
                        "payment_id": result.get("payment_id"),
                        "payment_status": result.get("payment_status"),
                        "transaction_id": transaction_id,
                        "error_code": result.get("error_code", 0),
                        "error_note": result.get("error_note")
                    }
                else:
                    payment.status = "failed"
                    db.commit()
                    return {
                        "success": False,
                        "transaction_id": transaction_id,
                        "error_code": response.status_code,
                        "error_note": f"HTTP Error: {response.status_code}"
                    }

        except Exception as e:
            if 'payment' in locals():
                payment.status = "failed"
                db.commit()
            return {
                "success": False,
                "error_code": -1,
                "error_note": f"To'lov yaratishda xatolik: {str(e)}"
            }

    async def delete_card_token(self, card_token: str) -> Dict[str, Any]:
        """Karta tokenini o'chirish"""
        try:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Auth": self._generate_auth_header()
            }

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/merchant/card_token/{self.service_id}/{card_token}",
                    headers=headers,
                    timeout=30.0
                )

                return {
                    "success": response.status_code == 200,
                    "error_code": 0 if response.status_code == 200 else response.status_code,
                    "error_note": None if response.status_code == 200 else f"HTTP Error: {response.status_code}"
                }

        except Exception as e:
            return {
                "success": False,
                "error_code": -1,
                "error_note": f"Token o'chirishda xatolik: {str(e)}"
            }


# Singleton instance
click_service = ClickService()