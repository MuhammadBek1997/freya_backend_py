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
from app.middleware import get_language, get_translation_function
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


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
        t = get_translation_function(language)
        
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
                message=t(f"{salon.name} saloni {request.duration} kunga top qilindi"),
                data={
                    "salon_id": request.salonId,
                    "salon_name": salon.name,
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
                message=t(f"{salon.name} saloni top'dan chiqarildi"),
                data={
                    "salon_id": request.salonId,
                    "salon_name": salon.name,
                    "is_top": False
                }
            )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Salon top qilish xatosi: {error}")
        db.rollback()
        t = get_translation_function(language)
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
                id=salon.id,
                name=salon.name,
                address=salon.address,
                phone=salon.phone,
                email=salon.email,
                is_active=salon.is_active,
                is_top=salon.is_top,
                rating=salon.rating,
                created_at=salon.created_at.isoformat(),
                updated_at=salon.updated_at.isoformat()
            )
            for salon in salons
        ]

    except Exception as error:
        logger.error(f"Top salonlar olish xatosi: {error}")
        t = get_translation_function(language)
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
                id=history.id,
                salon_id=history.salon_id,
                admin_id=history.admin_id,
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
        t = get_translation_function(language)
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
                Salon.name.ilike(f"%{search}%") |
                Salon.address.ilike(f"%{search}%")
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
                id=salon.id,
                name=salon.name,
                address=salon.address,
                phone=salon.phone,
                email=salon.email,
                is_active=salon.is_active,
                is_top=salon.is_top,
                rating=salon.rating,
                created_at=salon.created_at.isoformat(),
                updated_at=salon.updated_at.isoformat()
            )
            for salon in salons
        ]

    except Exception as error:
        logger.error(f"Salonlar ro'yxati olish xatosi: {error}")
        t = get_translation_function(language)
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
        t = get_translation_function(language)
        
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
            id=salon.id,
            name=salon.name,
            address=salon.address,
            phone=salon.phone,
            email=salon.email,
            description=salon.description,
            is_active=salon.is_active,
            is_top=salon.is_top,
            rating=salon.rating,
            photos=salon.photos or [],
            services=[
                {
                    "id": service.id,
                    "name": service.name,
                    "price": float(service.price),
                    "duration": service.duration
                }
                for service in services
            ],
            employees=[
                {
                    "id": employee.id,
                    "full_name": employee.full_name,
                    "phone": employee.phone,
                    "position": employee.position
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
        t = get_translation_function(language)
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
        t = get_translation_function(language)
        
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
        t = get_translation_function(language)
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
        t = get_translation_function(language)
        
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
        t = get_translation_function(language)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("SMS tasdiqlashda xatolik yuz berdi")
        )