"""
Admin routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models import Salon, Admin, SalonTopHistory, Employee, Service
from app.schemas.admin import (
    SalonTopRequest,
    SalonTopResponse,
    SalonListResponse,
    SalonDetailResponse,
    SalonTopHistoryResponse,
    SendSMSRequest,
    VerifySMSRequest,
    SMSResponse,
    SalonUpdateRequest,
    SalonPhotoUploadResponse
)
from app.auth import get_current_admin
from app.middleware import get_language
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

def get_translation(language: str):
    """Translation function for admin endpoints"""
    translations = {
        "en": {
            "Faqat adminlar salon top qilishi mumkin": "Only admins can feature salons",
            "Salon topilmadi": "Salon not found",
            "Salon muvaffaqiyatli top qilindi": "Salon successfully featured",
            "Salon top'dan muvaffaqiyatli chiqarildi": "Salon successfully unfeatured",
            "Server xatosi": "Server error",
            "Salon ro'yxati muvaffaqiyatli olindi": "Salon list retrieved successfully",
            "Salon ma'lumotlari muvaffaqiyatli olindi": "Salon details retrieved successfully",
            "Salon top tarixi muvaffaqiyatli olindi": "Salon feature history retrieved successfully",
            "Telefon raqam talab qilinadi": "Phone number is required",
            "SMS muvaffaqiyatli yuborildi": "SMS sent successfully",
            "SMS yuborishda xatolik": "Error sending SMS",
            "Tasdiqlash kodi talab qilinadi": "Verification code is required",
            "Noto'g'ri tasdiqlash kodi": "Invalid verification code",
            "SMS muvaffaqiyatli tasdiqlandi": "SMS verified successfully",
            "Salon ma'lumotlari muvaffaqiyatli yangilandi": "Salon information updated successfully",
            "Rasm muvaffaqiyatli yuklandi": "Image uploaded successfully"
        },
        "uz": {
            "Faqat adminlar salon top qilishi mumkin": "Faqat adminlar salon top qilishi mumkin",
            "Salon topilmadi": "Salon topilmadi",
            "Salon muvaffaqiyatli top qilindi": "Salon muvaffaqiyatli top qilindi",
            "Salon top'dan muvaffaqiyatli chiqarildi": "Salon top'dan muvaffaqiyatli chiqarildi",
            "Server xatosi": "Server xatosi",
            "Salon ro'yxati muvaffaqiyatli olindi": "Salon ro'yxati muvaffaqiyatli olindi",
            "Salon ma'lumotlari muvaffaqiyatli olindi": "Salon ma'lumotlari muvaffaqiyatli olindi",
            "Salon top tarixi muvaffaqiyatli olindi": "Salon top tarixi muvaffaqiyatli olindi",
            "Telefon raqam talab qilinadi": "Telefon raqam talab qilinadi",
            "SMS muvaffaqiyatli yuborildi": "SMS muvaffaqiyatli yuborildi",
            "SMS yuborishda xatolik": "SMS yuborishda xatolik",
            "Tasdiqlash kodi talab qilinadi": "Tasdiqlash kodi talab qilinadi",
            "Noto'g'ri tasdiqlash kodi": "Noto'g'ri tasdiqlash kodi",
            "SMS muvaffaqiyatli tasdiqlandi": "SMS muvaffaqiyatli tasdiqlandi",
            "Salon ma'lumotlari muvaffaqiyatli yangilandi": "Salon ma'lumotlari muvaffaqiyatli yangilandi",
            "Rasm muvaffaqiyatli yuklandi": "Rasm muvaffaqiyatli yuklandi"
        },
        "ru": {
            "Faqat adminlar salon top qilishi mumkin": "Только администраторы могут рекомендовать салоны",
            "Salon topilmadi": "Салон не найден",
            "Salon muvaffaqiyatli top qilindi": "Салон успешно рекомендован",
            "Salon top'dan muvaffaqiyatli chiqarildi": "Салон успешно удален из рекомендаций",
            "Server xatosi": "Ошибка сервера",
            "Salon ro'yxati muvaffaqiyatli olindi": "Список салонов успешно получен",
            "Salon ma'lumotlari muvaffaqiyatli olindi": "Информация о салоне успешно получена",
            "Salon top tarixi muvaffaqiyatli olindi": "История рекомендаций салона успешно получена",
            "Telefon raqam talab qilinadi": "Требуется номер телефона",
            "SMS muvaffaqiyatli yuborildi": "SMS успешно отправлено",
            "SMS yuborishda xatolik": "Ошибка при отправке SMS",
            "Tasdiqlash kodi talab qilinadi": "Требуется код подтверждения",
            "Noto'g'ri tasdiqlash kodi": "Неверный код подтверждения",
            "SMS muvaffaqiyatli tasdiqlandi": "SMS успешно подтверждено",
            "Salon ma'lumotlari muvaffaqiyatli yangilandi": "Информация о салоне успешно обновлена",
            "Rasm muvaffaqiyatli yuklandi": "Изображение успешно загружено"
        }
    }
    
    lang_code = language.lower()[:2] if language else "uz"
    if lang_code not in translations:
        lang_code = "uz"
    
    return lambda key: translations[lang_code].get(key, key)


@router.post("/salon/top", response_model=SalonTopResponse)
async def set_salon_top(
    request: SalonTopRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
    language: str = Depends(get_language)
):
    """
    Salonni top qilish yoki top'dan chiqarish
    """
    try:
        t = get_translation(language)
        
        # Admin ekanligini tekshirish
        if current_admin.role not in ['admin', 'superadmin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=t("Faqat adminlar salon top qilishi mumkin")
            )

        # Salon mavjudligini tekshirish
        salon = db.query(Salon).filter(Salon.id == request.salonId).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=t("Salon topilmadi")
            )

        if request.isTop:
            # Salon top qilish
            end_date = datetime.now() + timedelta(days=request.duration)

            # Salon is_top ni true qilish
            salon.is_top = True
            
            # Avvalgi active top historyni tugatish
            active_histories = db.query(SalonTopHistory).filter(
                SalonTopHistory.salon_id == request.salonId,
                SalonTopHistory.is_active == True
            ).all()
            
            for history in active_histories:
                history.is_active = False
                history.end_date = datetime.now()

            # Yangi top history qo'shish
            new_history = SalonTopHistory(
                salon_id=request.salonId,
                admin_id=current_admin.id,
                action="top",
                end_date=end_date,
                is_active=True
            )
            db.add(new_history)

            db.commit()

            return SalonTopResponse(
                success=True,
                message=t(f"{salon.salon_name} saloni {request.duration} kunga top qilindi"),
                data={
                    "salon_id": request.salonId,
                    "salon_name": salon.salon_name,
                    "is_top": True,
                    "duration": request.duration,
                    "end_date": end_date.isoformat()
                }
            )
        else:
            # Salon top'dan chiqarish
            salon.is_top = False
            
            # Active top historyni tugatish
            active_histories = db.query(SalonTopHistory).filter(
                SalonTopHistory.salon_id == request.salonId,
                SalonTopHistory.is_active == True
            ).all()
            
            for history in active_histories:
                history.is_active = False
                history.end_date = datetime.now()

            # Yangi untop history qo'shish
            new_history = SalonTopHistory(
                salon_id=request.salonId,
                admin_id=current_admin.id,
                action="untop",
                is_active=False
            )
            db.add(new_history)

            db.commit()

            return SalonTopResponse(
                success=True,
                message=t(f"{salon.salon_name} saloni top'dan chiqarildi"),
                data={
                    "salon_id": request.salonId,
                    "salon_name": salon.salon_name,
                    "is_top": False
                }
            )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Salon top qilish xatosi: {error}")
        db.rollback()
        t = get_translation(language)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("Server xatosi")
        )


@router.get("/salons/top", response_model=List[SalonListResponse])
async def get_top_salons(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
    language: str = Depends(get_language)
):
    """
    Top salonlar ro'yxatini olish
    """
    try:
        salons = db.query(Salon).filter(
            Salon.is_top == True,
            Salon.is_active == True
        ).order_by(desc(Salon.updated_at)).all()

        return [
            SalonListResponse(
                id=str(salon.id),
                name=salon.salon_name,
                address=salon.address_uz or salon.address_ru or salon.address_en or "",
                phone=salon.salon_phone or "",
                email="",  # Salon modelida email yo'q
                is_active=salon.is_active,
                is_top=salon.is_top,
                rating=float(salon.salon_rating) if salon.salon_rating else 0.0,
                created_at=salon.created_at.isoformat(),
                updated_at=salon.updated_at.isoformat()
            )
            for salon in salons
        ]

    except Exception as error:
        logger.error(f"Top salonlar olish xatosi: {error}")
        t = get_translation(language)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("Server xatosi")
        )


@router.get("/salon/{salon_id}/top-history", response_model=List[SalonTopHistoryResponse])
async def get_salon_top_history(
    salon_id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
    language: str = Depends(get_language)
):
    """
    Salon top tarixini olish
    """
    try:
        histories = db.query(SalonTopHistory).filter(
            SalonTopHistory.salon_id == salon_id
        ).order_by(desc(SalonTopHistory.created_at)).all()

        return [
            SalonTopHistoryResponse(
                id=str(history.id),
                salon_id=str(history.salon_id),
                admin_id=str(history.admin_id),
                action=history.action,
                start_date=history.start_date.isoformat(),
                end_date=history.end_date.isoformat() if history.end_date else None,
                is_active=history.is_active,
                created_at=history.created_at.isoformat()
            )
            for history in histories
        ]

    except Exception as error:
        logger.error(f"Salon top tarixi olish xatosi: {error}")
        t = get_translation(language)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("Server xatosi")
        )


@router.get("/salons", response_model=List[SalonListResponse])
async def get_all_salons(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_top: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
    language: str = Depends(get_language)
):
    """
    Barcha salonlar ro'yxatini olish (pagination bilan)
    """
    try:
        query = db.query(Salon)

        # Filtrlar
        if search:
            query = query.filter(
                Salon.salon_name.ilike(f"%{search}%") |
                Salon.address_uz.ilike(f"%{search}%")
            )
        
        if is_top is not None:
            query = query.filter(Salon.is_top == is_top)
            
        if is_active is not None:
            query = query.filter(Salon.is_active == is_active)

        # Pagination
        offset = (page - 1) * limit
        salons = query.order_by(desc(Salon.created_at)).offset(offset).limit(limit).all()

        return [
            SalonListResponse(
                id=str(salon.id),
                name=salon.salon_name,
                address=salon.address_uz or salon.address_ru or salon.address_en or "",
                phone=salon.salon_phone or "",
                email="",
                is_active=salon.is_active,
                is_top=salon.is_top,
                rating=float(salon.salon_rating) if salon.salon_rating else 0.0,
                created_at=salon.created_at.isoformat(),
                updated_at=salon.updated_at.isoformat()
            )
            for salon in salons
        ]

    except Exception as error:
        logger.error(f"Salonlar ro'yxati olish xatosi: {error}")
        t = get_translation(language)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("Server xatosi")
        )


@router.get("/my-salon", response_model=SalonDetailResponse)
async def get_my_salon(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
    language: str = Depends(get_language)
):
    """
    Admin'ning o'z salonini olish
    """
    try:
        t = get_translation(language)
        
        if not current_admin.salon_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=t("Sizga biriktirilgan salon topilmadi")
            )

        salon = db.query(Salon).filter(Salon.id == current_admin.salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=t("Salon topilmadi")
            )

        # Salon xodimlarini olish
        employees = db.query(Employee).filter(
            Employee.salon_id == salon.id,
            Employee.is_active == True
        ).all()

        # Salon xizmatlarini olish
        services = db.query(Service).filter(
            Service.salon_id == salon.id,
            Service.is_active == True
        ).all()

        return SalonDetailResponse(
            id=str(salon.id),
            name=salon.salon_name,
            address=salon.address_uz or salon.address_ru or salon.address_en or "",
            phone=salon.salon_phone or "",
            email="",
            description=salon.salon_description or "",
            is_active=salon.is_active,
            is_top=salon.is_top,
            rating=float(salon.salon_rating) if salon.salon_rating else 0.0,
            photos=[],
            services=[
                {
                    "id": str(service.id),
                    "name": service.name,
                    "price": float(service.price),
                    "duration": service.duration
                }
                for service in services
            ],
            employees=[
                {
                    "id": str(employee.id),
                    "full_name": f"{employee.name} {employee.surname or ''}".strip(),
                    "phone": employee.phone,
                    "role": employee.role
                }
                for employee in employees
            ],
            created_at=salon.created_at.isoformat(),
            updated_at=salon.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Salon ma'lumotlari olish xatosi: {error}")
        t = get_translation(language)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("Server xatosi")
        )


@router.post("/send-sms", response_model=SMSResponse)
async def send_sms(
    request: SendSMSRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
    language: str = Depends(get_language)
):
    """
    SMS yuborish (admin uchun)
    """
    try:
        t = get_translation(language)
        
        # TODO: SMS service integration
        # sms_service = SMSService()
        # result = await sms_service.send_sms(request.phone, request.message)
        
        # Hozircha mock response
        return SMSResponse(
            success=True,
            message=t("SMS muvaffaqiyatli yuborildi"),
            data={
                "phone": request.phone,
                "message": request.message,
                "sent_at": datetime.now().isoformat()
            }
        )

    except Exception as error:
        logger.error(f"SMS yuborish xatosi: {error}")
        t = get_translation(language)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("SMS yuborishda xatolik yuz berdi")
        )


@router.post("/verify-sms", response_model=SMSResponse)
async def verify_sms(
    request: VerifySMSRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
    language: str = Depends(get_language)
):
    """
    SMS kodni tasdiqlash (admin uchun)
    """
    try:
        t = get_translation(language)
        
        # TODO: SMS verification logic
        # sms_service = SMSService()
        # is_valid = await sms_service.verify_code(request.phone, request.code)
        
        # Hozircha mock verification
        is_valid = request.code == "123456"  # Mock code
        
        if is_valid:
            return SMSResponse(
                success=True,
                message=t("SMS kod muvaffaqiyatli tasdiqlandi"),
                data={
                    "phone": request.phone,
                    "verified": True,
                    "verified_at": datetime.now().isoformat()
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=t("Noto'g'ri SMS kod")
            )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"SMS tasdiqlash xatosi: {error}")
        t = get_translation(language)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("SMS tasdiqlashda xatolik yuz berdi")
        )