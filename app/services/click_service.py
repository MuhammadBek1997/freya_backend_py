import hashlib
import httpx
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

    async def create_employee_post_payment(self, employee_id: int, post_count: int = 4, db: Session = None) -> Dict[str, Any]:
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

    async def create_user_premium_payment(self, user_id: int, duration: int = 30, db: Session = None) -> Dict[str, Any]:
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

    async def create_salon_top_payment(self, salon_id: int, admin_id: int, duration: int = 7, db: Session = None) -> Dict[str, Any]:
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


# Singleton instance
click_service = ClickService()