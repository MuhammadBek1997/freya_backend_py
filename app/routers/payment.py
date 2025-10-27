from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import hashlib
from app.database import get_db
from app.services.click_service import click_service
from app.middleware.auth import get_current_user, get_current_admin
from app.middleware.rate_limiter import check_rate_limit, check_card_token_rate_limit
from app.utils.payment_validator import PaymentValidator
from app.models import User, Admin, Payment
from app.models.payment_card import PaymentCard
from app.schemas.user import (
    CardTokenRequest,
    CardTokenResponse,
    DirectCardPaymentRequest,
    DirectCardPaymentResponse,
    PaymentCardResponse,
)
from pydantic import BaseModel


class EmployeePostPaymentRequest(BaseModel):
    employee_id: str
    post_count: int = 4


class UserPremiumPaymentRequest(BaseModel):
    user_id: str
    duration: int = 30  # 30 yoki 90 kun


class SalonTopPaymentRequest(BaseModel):
    salon_id: str
    duration: int = 7  # 7 yoki 30 kun


class PaymentStatusRequest(BaseModel):
    transaction_id: str


class PaymentCallbackRequest(BaseModel):
    transaction_id: str
    click_trans_id: str
    status: str
    sign: Optional[str] = None  # Click imzosi (ixtiyoriy)
    merchant_id: Optional[str] = None
    service_id: Optional[str] = None
    amount: Optional[int] = None


router = APIRouter(prefix="/payment", tags=["Payment"])


def _detect_card_type(card_number: str) -> str:
    """Detect card type from card number (basic prefixes)."""
    if not card_number:
        return "Unknown"
    if card_number.startswith("4"):
        return "Visa"
    elif card_number.startswith(("51", "52", "53", "54", "55")):
        return "MasterCard"
    elif card_number.startswith("9860"):
        return "Uzcard"
    elif card_number.startswith("8600"):
        return "Humo"
    else:
        return "Unknown"


@router.post("/employee-post", summary="Employee post uchun to'lov yaratish")
async def create_employee_post_payment(
    request: EmployeePostPaymentRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Employee post uchun to'lov yaratish
    
    - **employee_id**: Employee ID
    - **post_count**: Post soni (default: 4)
    """
    try:
        result = await click_service.create_employee_post_payment(
            employee_id=request.employee_id,
            post_count=request.post_count,
            db=db
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": "To'lov muvaffaqiyatli yaratildi",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"To'lov yaratishda xatolik: {str(e)}"
        )


@router.post("/user-premium", summary="User premium uchun to'lov yaratish")
async def create_user_premium_payment(
    request: UserPremiumPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    User premium uchun to'lov yaratish
    
    - **user_id**: User ID
    - **duration**: Davomiyligi (30 yoki 90 kun)
    """
    try:
        # Foydalanuvchi faqat o'zining premium to'lovini yarata oladi
        if current_user.id != request.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Siz faqat o'zingizning premium to'lovingizni yarata olasiz"
            )
        
        result = await click_service.create_user_premium_payment(
            user_id=request.user_id,
            duration=request.duration,
            db=db
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": "To'lov muvaffaqiyatli yaratildi",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"To'lov yaratishda xatolik: {str(e)}"
        )


@router.post("/salon-top", summary="Salon top uchun to'lov yaratish")
async def create_salon_top_payment(
    request: SalonTopPaymentRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Salon top uchun to'lov yaratish
    
    - **salon_id**: Salon ID
    - **duration**: Davomiyligi (7 yoki 30 kun)
    """
    try:
        result = await click_service.create_salon_top_payment(
            salon_id=request.salon_id,
            admin_id=current_admin.id,
            duration=request.duration,
            db=db
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": "To'lov muvaffaqiyatli yaratildi",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"To'lov yaratishda xatolik: {str(e)}"
        )


@router.get("/status/{transaction_id}", summary="To'lov holatini tekshirish")
async def check_payment_status(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    To'lov holatini tekshirish
    
    - **transaction_id**: Transaction ID
    """
    try:
        # Foydalanuvchi faqat o'zining to'lovlarini ko'ra oladi
        payment = db.query(Payment).filter(Payment.transaction_id == transaction_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="To'lov topilmadi"
            )
        
        if not payment.user_id or payment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Siz faqat o'zingizning to'lovlaringizni ko'ra olasiz"
            )
        
        result = await click_service.check_payment_status(transaction_id)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"To'lov holatini tekshirishda xatolik: {str(e)}"
        )


@router.post("/callback", summary="Click.uz callback")
async def payment_callback(
    request: PaymentCallbackRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Click.uz dan kelgan callback
    
    - **transaction_id**: Transaction ID
    - **click_trans_id**: Click transaction ID
    - **status**: To'lov holati
    - **sign**: Imzo (ixtiyoriy) – tekshiruv uchun
    """
    try:
        payment = db.query(Payment).filter(Payment.transaction_id == request.transaction_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="To'lov topilmadi"
            )

        # Idempotency: agar allaqachon yakunlangan bo'lsa, qaytamiz
        if payment.status == "completed":
            return {"success": True, "message": "Allaqachon yakunlangan", "transaction_id": request.transaction_id}

        # Optional signature verification (agar sign bor bo'lsa)
        if request.sign and request.merchant_id and request.service_id:
            params = {
                "merchant_id": request.merchant_id,
                "service_id": request.service_id,
                "transaction_param": request.transaction_id
            }
            if request.amount is not None:
                params["amount"] = request.amount
            expected = click_service.generate_signature(params)
            if expected != request.sign:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Imzo mos kelmadi"
                )

        if request.status == "success":
            result = await click_service.handle_successful_payment(
                transaction_id=request.transaction_id,
                click_trans_id=request.click_trans_id,
                db=db
            )
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
            
            return {
                "success": True,
                "message": "To'lov muvaffaqiyatli yakunlandi",
                "transaction_id": request.transaction_id
            }
        else:
            # Failed/cancelled
            payment.status = "failed"
            payment.updated_at = payment.updated_at  # trigger onupdate
            db.commit()
            return {"success": False, "message": "To'lov bajarilmadi", "transaction_id": request.transaction_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Callbackda xatolik: {str(e)}"
        )


@router.get("/admin/status/{transaction_id}", summary="Admin: to'lov holatini tekshirish")
async def admin_check_payment_status(
    transaction_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin uchun to'lov holatini tekshirish
    
    - **transaction_id**: Transaction ID
    """
    try:
        payment = db.query(Payment).filter(Payment.transaction_id == transaction_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="To'lov topilmadi"
            )
        result = await click_service.check_payment_status(transaction_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"To'lov holatini tekshirishda xatolik: {str(e)}"
        )


@router.get("/history", summary="To'lov tarixi")
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Foydalanuvchi to'lov tarixi
    """
    try:
        payments = db.query(Payment).filter(Payment.user_id == current_user.id).order_by(Payment.created_at.desc()).all()
        data = [
            {
                "id": p.id,
                "amount": p.amount,
                "type": p.payment_type,
                "transaction_id": p.transaction_id,
                "status": p.status,
                "created_at": p.created_at,
            }
            for p in payments
        ]
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tarixni olishda xatolik: {str(e)}"
        )


# Karta tokenizatsiyasi endpointlari
@router.post("/card-token/create", response_model=CardTokenResponse, summary="Karta tokenini yaratish")
async def create_card_token(
    request: CardTokenRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(check_card_token_rate_limit)
) -> CardTokenResponse:
    """
    Karta ma'lumotlarini tokenizatsiya qilish
    
    Rate limit: 3 so'rov 5 daqiqada
    """
    try:
        # Qo'shimcha validatsiya
        if not PaymentValidator.validate_card_number(request.card_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Karta raqami noto'g'ri formatda"
            )
        
        # Schema: expiry_month/expiry_year — shunga mos ishlatamiz
        if not PaymentValidator.validate_expiry_date(request.expiry_month, request.expiry_year):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Karta amal qilish muddati noto'g'ri yoki o'tgan"
            )
        
        # Karta raqamini tozalash
        clean_card_number = PaymentValidator.sanitize_card_number(request.card_number)
        
        result = await click_service.create_card_token({
            "card_number": clean_card_number,
            "expiry_month": request.expiry_month,
            "expiry_year": request.expiry_year,
            "temporary": getattr(request, "temporary", True)
        })
        
        if not result.get("success") or not result.get("card_token"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error_note") or "Karta tokenini yaratishda xatolik"
            )
        
        # Persist card in payment_cards upon successful token creation (idempotent)
        try:
            # Build encrypted fingerprint (hash) and last four
            encrypted = hashlib.sha256(clean_card_number.encode()).hexdigest()
            last_four = clean_card_number[-4:] if len(clean_card_number) >= 4 else clean_card_number

            # Skip if already exists for this user
            existing = db.query(PaymentCard).filter(
                PaymentCard.user_id == current_user.id,
                PaymentCard.card_number_encrypted == encrypted,
            ).first()

            if not existing:
                # Determine default: first card becomes default
                user_cards_count = db.query(PaymentCard).filter(PaymentCard.user_id == current_user.id).count()
                is_default = user_cards_count == 0

                card = PaymentCard(
                    user_id=str(current_user.id),
                    card_number_encrypted=encrypted,
                    card_holder_name=request.card_holder_name,
                    expiry_month=request.expiry_month,
                    expiry_year=request.expiry_year,
                    card_type=_detect_card_type(clean_card_number),
                    phone_number=(request.phone_number or current_user.phone or ""),
                    is_default=is_default,
                    is_active=True,
                    last_four_digits=last_four,
                )
                db.add(card)
                db.commit()
        except Exception:
            # Do not break token creation flow if persistence fails
            db.rollback()

        return CardTokenResponse(
            success=True,
            card_token=result.get("card_token"),
            phone_number=result.get("phone_number"),
            temporary=result.get("temporary", True),
            error_code=result.get("error_code"),
            error_note=result.get("error_note")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Karta tokenini yaratishda xatolik: {str(e)}"
        )


@router.post("/card-token/verify", summary="Karta tokenini tasdiqlash")
async def verify_card_token(
    card_token: str,
    sms_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    SMS kod orqali karta tokenini tasdiqlash
    """
    try:
        result = await click_service.verify_card_token(card_token, sms_code)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Karta tokenini tasdiqlashda xatolik")
            )
        
        return {
            "success": True,
            "message": "Karta tokeni muvaffaqiyatli tasdiqlandi"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Karta tokenini tasdiqlashda xatolik: {str(e)}"
        )


@router.delete("/card-token/{card_token}", summary="Karta tokenini o'chirish")
async def delete_card_token(
    card_token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Karta tokenini o'chirish
    """
    try:
        result = await click_service.delete_card_token(card_token)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Karta tokenini o'chirishda xatolik")
            )
        
        return {
            "success": True,
            "message": "Karta tokeni muvaffaqiyatli o'chirildi"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Karta tokenini o'chirishda xatolik: {str(e)}"
        )


# To'g'ridan-to'g'ri karta to'lovi endpointlari
@router.post("/direct/employee-post", response_model=DirectCardPaymentResponse, summary="Employee post uchun to'g'ridan-to'g'ri karta to'lovi")
async def create_direct_employee_post_payment(
    request: DirectCardPaymentRequest,
    http_request: Request,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    _: None = Depends(lambda req: check_rate_limit(req, max_requests=5, window_seconds=60))
) -> DirectCardPaymentResponse:
    """
    Employee post uchun to'g'ridan-to'g'ri karta to'lovi
    
    Rate limit: 5 so'rov 1 daqiqada
    """
    try:
        # Miqdor validatsiyasi
        if not PaymentValidator.validate_amount(request.amount, "employee_post"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="To'lov miqdori noto'g'ri (1,000 - 1,000,000 so'm)"
            )
        
        # Employee ID validatsiyasi
        if not request.employee_id or not request.employee_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee ID talab qilinadi"
            )
        
        result = await click_service.create_direct_card_payment({
            "card_token": request.card_token,
            "amount": request.amount,
            "payment_type": "employee_post",
            "employee_id": request.employee_id,
            "user_id": None,
            "salon_id": None
        }, db=db)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "To'lovni amalga oshirishda xatolik")
            )
        
        return DirectCardPaymentResponse(
            success=True,
            transaction_id=result.get("transaction_id"),
            payment_id=str(result.get("payment_id")) if result.get("payment_id") is not None else None,
            payment_status=result.get("payment_status"),
            error_code=result.get("error_code"),
            error_note=result.get("error_note")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"To'lovni amalga oshirishda xatolik: {str(e)}"
        )


@router.post("/direct/user-premium", response_model=DirectCardPaymentResponse, summary="User premium uchun to'g'ridan-to'g'ri karta to'lovi")
async def create_direct_user_premium_payment(
    request: DirectCardPaymentRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(lambda req: check_rate_limit(req, max_requests=3, window_seconds=300))
) -> DirectCardPaymentResponse:
    """
    User premium uchun to'g'ridan-to'g'ri karta to'lovi
    
    Rate limit: 3 so'rov 5 daqiqada
    """
    try:
        # Miqdor validatsiyasi
        if not PaymentValidator.validate_amount(request.amount, "user_premium"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="To'lov miqdori noto'g'ri (5,000 - 500,000 so'm)"
            )
        
        result = await click_service.create_direct_card_payment({
            "card_token": request.card_token,
            "amount": request.amount,
            "payment_type": "user_premium",
            "employee_id": None,
            "user_id": str(current_user.id),
            "salon_id": None
        }, db=db)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "To'lovni amalga oshirishda xatolik")
            )
        
        return DirectCardPaymentResponse(
            success=True,
            transaction_id=result.get("transaction_id"),
            payment_id=str(result.get("payment_id")) if result.get("payment_id") is not None else None,
            payment_status=result.get("payment_status"),
            error_code=result.get("error_code"),
            error_note=result.get("error_note")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"To'lovni amalga oshirishda xatolik: {str(e)}"
        )


@router.post("/direct/salon-top", response_model=DirectCardPaymentResponse, summary="Salon top uchun to'g'ridan-to'g'ri karta to'lovi")
async def create_direct_salon_top_payment(
    request: DirectCardPaymentRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(lambda req: check_rate_limit(req, max_requests=3, window_seconds=300))
) -> DirectCardPaymentResponse:
    """
    Salon top uchun to'g'ridan-to'g'ri karta to'lovi
    
    Rate limit: 3 so'rov 5 daqiqada
    """
    try:
        # Miqdor validatsiyasi
        if not PaymentValidator.validate_amount(request.amount, "salon_top"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="To'lov miqdori noto'g'ri (10,000 - 2,000,000 so'm)"
            )
        
        # Salon ID validatsiyasi
        if not request.salon_id or not request.salon_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Salon ID talab qilinadi"
            )
        
        result = await click_service.create_direct_card_payment({
            "card_token": request.card_token,
            "amount": request.amount,
            "payment_type": "salon_top",
            "employee_id": None,
            "user_id": str(current_user.id),
            "salon_id": request.salon_id
        }, db=db)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "To'lovni amalga oshirishda xatolik")
            )
        
        return DirectCardPaymentResponse(
            success=True,
            transaction_id=result.get("transaction_id"),
            payment_id=str(result.get("payment_id")) if result.get("payment_id") is not None else None,
            payment_status=result.get("payment_status"),
            error_code=result.get("error_code"),
            error_note=result.get("error_note")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"To'lovni amalga oshirishda xatolik: {str(e)}"
        )


@router.get("/cards", response_model=List[PaymentCardResponse], summary="Foydalanuvchi kartalarini olish")
async def get_payment_cards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PaymentCardResponse]:
    """
    Foydalanuvchining to'lov kartalari ro'yxatini qaytaradi.
    Default kartalar birinchi, so'ngra yaratilgan vaqti bo'yicha.
    """
    cards = (
        db.query(PaymentCard)
        .filter(PaymentCard.user_id == current_user.id)
        .order_by(PaymentCard.is_default.desc(), PaymentCard.created_at.desc())
        .all()
    )

    return [
        PaymentCardResponse(
            id=c.id,
            masked_card_number=f"**** **** **** {c.last_four_digits}",
            card_type=c.card_type or "Unknown",
            card_holder_name=c.card_holder_name,
            expiry_month=c.expiry_month,
            expiry_year=c.expiry_year,
            is_default=c.is_default,
            created_at=c.created_at,
        )
        for c in cards
    ]