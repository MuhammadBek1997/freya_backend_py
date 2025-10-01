from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database import get_db
from app.services.click_service import click_service
from app.middleware.auth import get_current_user, get_current_admin
from app.models import User, Admin, Payment
from pydantic import BaseModel


class EmployeePostPaymentRequest(BaseModel):
    employee_id: int
    post_count: int = 4


class UserPremiumPaymentRequest(BaseModel):
    user_id: int
    duration: int = 30  # 30 yoki 90 kun


class SalonTopPaymentRequest(BaseModel):
    salon_id: int
    duration: int = 7  # 7 yoki 30 kun


class PaymentStatusRequest(BaseModel):
    transaction_id: str


class PaymentCallbackRequest(BaseModel):
    transaction_id: str
    click_trans_id: str
    status: str


router = APIRouter(prefix="/payment", tags=["Payment"])


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
        
        if payment.user_id != current_user.id:
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
    """
    try:
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
                "message": "To'lov muvaffaqiyatli qayta ishlandi"
            }
        else:
            # To'lov muvaffaqiyatsiz bo'lgan holat
            payment = db.query(Payment).filter(Payment.transaction_id == request.transaction_id).first()
            if payment:
                payment.status = "failed"
                db.commit()
            
            return {
                "success": False,
                "message": "To'lov muvaffaqiyatsiz"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Callback qayta ishlashda xatolik: {str(e)}"
        )


@router.get("/history", summary="To'lov tarixi")
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Foydalanuvchining to'lov tarixi
    """
    try:
        payments = db.query(Payment).filter(Payment.user_id == current_user.id).all()
        
        payment_list = []
        for payment in payments:
            payment_list.append({
                "id": payment.id,
                "amount": payment.amount,
                "payment_type": payment.payment_type,
                "transaction_id": payment.transaction_id,
                "status": payment.status,
                "description": payment.description,
                "created_at": payment.created_at,
                "updated_at": payment.updated_at
            })
        
        return {
            "success": True,
            "data": payment_list
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"To'lov tarixini olishda xatolik: {str(e)}"
        )