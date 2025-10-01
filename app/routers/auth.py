"""
Authentication routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Admin, Employee
from app.schemas.auth import (
    LoginRequest, 
    LoginResponse, 
    CreateAdminRequest, 
    AdminProfileResponse,
    TokenResponse
)
from app.auth import JWTUtils, get_current_superadmin, get_current_admin
from app.middleware import get_language, get_translation_function
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/superadmin/login", response_model=LoginResponse)
async def superadmin_login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Superadmin login endpoint
    """
    try:
        # Set default language for this endpoint
        language = "en"
        
        # Simple translation function for this endpoint
        def t(key: str) -> str:
            translations = {
                "en": {
                    "Username va password talab qilinadi": "Username and password are required",
                    "Noto'g'ri username yoki password": "Invalid username or password",
                    "Superadmin muvaffaqiyatli login qildi": "Superadmin logged in successfully",
                    "Server xatosi": "Server error"
                },
                "uz": {
                    "Username va password talab qilinadi": "Username va password talab qilinadi",
                    "Noto'g'ri username yoki password": "Noto'g'ri username yoki password",
                    "Superadmin muvaffaqiyatli login qildi": "Superadmin muvaffaqiyatli login qildi",
                    "Server xatosi": "Server xatosi"
                },
                "ru": {
                    "Username va password talab qilinadi": "Требуется имя пользователя и пароль",
                    "Noto'g'ri username yoki password": "Неверное имя пользователя или пароль",
                    "Superadmin muvaffaqiyatli login qildi": "Суперадмин успешно вошел в систему",
                    "Server xatosi": "Ошибка сервера"
                }
            }
            lang_translations = translations.get(language, translations["en"])
            return lang_translations.get(key, key)
        
        if not request.username or not request.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=t("Username va password talab qilinadi")
            )

        # Superadmin ni database dan topish
        superadmin = db.query(Admin).filter(
            Admin.username == request.username,
            Admin.role == "superadmin",
            Admin.is_active == True
        ).first()

        if not superadmin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=t("Noto'g'ri username yoki password")
            )

        # Password tekshirish
        is_valid_password = JWTUtils.verify_password(request.password, superadmin.password_hash)
        
        if not is_valid_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=t("Noto'g'ri username yoki password")
            )

        # Token yaratish
        token = JWTUtils.create_access_token({
            "id": str(superadmin.id),  # Convert UUID to string
            "username": superadmin.username,
            "role": "superadmin"
        })

        return LoginResponse(
            message=t("Superadmin muvaffaqiyatli login qildi"),
            token=token,
            user={
                "id": str(superadmin.id),  # Convert UUID to string
                "username": superadmin.username,
                "email": superadmin.email,
                "full_name": superadmin.full_name,
                "role": "superadmin"
            }
        )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Superadmin login xatosi: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("Server xatosi")
        )


@router.post("/admin/login", response_model=LoginResponse)
async def admin_login(
    request: LoginRequest,
    db: Session = Depends(get_db),
    language: str = Depends(get_language)
):
    """
    Admin login endpoint
    """
    try:
        # Simple translation function
        def t(key: str) -> str:
            translations = {
                "en": {
                    "Username va password talab qilinadi": "Username and password are required",
                    "Noto'g'ri username yoki password": "Invalid username or password",
                    "Admin muvaffaqiyatli login qildi": "Admin logged in successfully",
                    "Server xatosi": "Server error"
                },
                "uz": {
                    "Username va password talab qilinadi": "Username va password talab qilinadi",
                    "Noto'g'ri username yoki password": "Noto'g'ri username yoki password",
                    "Admin muvaffaqiyatli login qildi": "Admin muvaffaqiyatli login qildi",
                    "Server xatosi": "Server xatosi"
                },
                "ru": {
                    "Username va password talab qilinadi": "Требуется имя пользователя и пароль",
                    "Noto'g'ri username yoki password": "Неверное имя пользователя или пароль",
                    "Admin muvaffaqiyatli login qildi": "Администратор успешно вошел в систему",
                    "Server xatosi": "Ошибка сервера"
                }
            }
            lang_translations = translations.get(language, translations["uz"])
            return lang_translations.get(key, key)
        
        logger.info(f"Admin login attempt: {request.username}")

        if not request.username or not request.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=t("Username va password talab qilinadi")
            )

        # Admin ni database dan topish
        admin = db.query(Admin).filter(
            Admin.username == request.username,
            Admin.is_active == True
        ).first()

        logger.info(f"Admin found in database: {admin.id if admin else 'Not found'}")

        if not admin:
            logger.info("Admin not found or inactive")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=t("Noto'g'ri username yoki password")
            )

        # Password tekshirish
        logger.info("Comparing password...")
        is_valid_password = JWTUtils.verify_password(request.password, admin.password_hash)
        
        if not is_valid_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=t("Noto'g'ri username yoki password")
            )

        # Token yaratish
        token = JWTUtils.create_access_token({
            "id": str(admin.id),
            "username": admin.username,
            "role": admin.role
        })

        return LoginResponse(
            message=t("Admin muvaffaqiyatli login qildi"),
            token=token,
            user={
                "id": str(admin.id),
                "username": admin.username,
                "email": admin.email,
                "full_name": admin.full_name,
                "role": admin.role,
                "salon_id": str(admin.salon_id) if admin.salon_id else None
            }
        )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Admin login xatosi: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("Server xatosi")
        )


@router.post("/admin/create", response_model=dict)
async def create_admin(
    request: CreateAdminRequest,
    db: Session = Depends(get_db),
    current_superadmin: Admin = Depends(get_current_superadmin),
    language: str = Depends(get_language)
):
    """
    Create admin endpoint (superadmin only)
    """
    try:
        # Simple translation function
        def t(key: str) -> str:
            translations = {
                "en": {
                    "Bu username allaqachon mavjud": "This username already exists",
                    "Bu email allaqachon mavjud": "This email already exists", 
                    "Admin muvaffaqiyatli yaratildi": "Admin created successfully",
                    "Server xatosi": "Server error"
                },
                "uz": {
                    "Bu username allaqachon mavjud": "Bu username allaqachon mavjud",
                    "Bu email allaqachon mavjud": "Bu email allaqachon mavjud",
                    "Admin muvaffaqiyatli yaratildi": "Admin muvaffaqiyatli yaratildi", 
                    "Server xatosi": "Server xatosi"
                },
                "ru": {
                    "Bu username allaqachon mavjud": "Это имя пользователя уже существует",
                    "Bu email allaqachon mavjud": "Этот email уже существует",
                    "Admin muvaffaqiyatli yaratildi": "Администратор успешно создан",
                    "Server xatosi": "Ошибка сервера"
                }
            }
            lang_translations = translations.get(language, translations["uz"])
            return lang_translations.get(key, key)
        
        # Username mavjudligini tekshirish
        existing_admin = db.query(Admin).filter(Admin.username == request.username).first()
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=t("Bu username allaqachon mavjud")
            )

        # Email mavjudligini tekshirish
        existing_email = db.query(Admin).filter(Admin.email == request.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=t("Bu email allaqachon mavjud")
            )

        # Password hash qilish
        password_hash = JWTUtils.hash_password(request.password)

        # Yangi admin yaratish
        new_admin = Admin(
            username=request.username,
            email=request.email,
            password_hash=password_hash,
            full_name=request.full_name,
            role=request.role,
            salon_id=request.salon_id,
            is_active=True
        )

        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        return {
            "message": t("Admin muvaffaqiyatli yaratildi"),
            "admin": {
                "id": new_admin.id,
                "username": new_admin.username,
                "email": new_admin.email,
                "full_name": new_admin.full_name,
                "role": new_admin.role,
                "salon_id": new_admin.salon_id
            }
        }

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Admin yaratish xatosi: {error}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("Server xatosi")
        )


@router.post("/employee/login", response_model=LoginResponse)
async def employee_login(
    request: LoginRequest,
    db: Session = Depends(get_db),
    language: str = Depends(get_language)
):
    """
    Employee login endpoint
    """
    try:
        # Simple translation function
        def t(key):
            translations = {
                "Username va password talab qilinadi": {
                    "en": "Username and password are required",
                    "uz": "Username va password talab qilinadi",
                    "ru": "Требуются имя пользователя и пароль"
                },
                "Noto'g'ri username yoki password": {
                    "en": "Invalid username or password",
                    "uz": "Noto'g'ri username yoki password",
                    "ru": "Неверное имя пользователя или пароль"
                },
                "Employee muvaffaqiyatli login qildi": {
                    "en": "Employee logged in successfully",
                    "uz": "Employee muvaffaqiyatli login qildi",
                    "ru": "Сотрудник успешно вошел в систему"
                },
                "Server xatosi": {
                    "en": "Server error",
                    "uz": "Server xatosi",
                    "ru": "Ошибка сервера"
                }
            }
            return translations.get(key, {}).get(language, key)
        
        if not request.username or not request.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=t("Username va password talab qilinadi")
            )

        # Employee ni database dan topish
        employee = db.query(Employee).filter(
            Employee.username == request.username,
            Employee.is_active == True
        ).first()

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=t("Noto'g'ri username yoki password")
            )

        # Password tekshirish
        is_valid_password = JWTUtils.verify_password(request.password, employee.employee_password)
        
        if not is_valid_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=t("Noto'g'ri username yoki password")
            )

        # Token yaratish
        token = JWTUtils.create_access_token({
            "id": str(employee.id),
            "username": employee.username,
            "role": "employee"
        })

        return LoginResponse(
            message=t("Employee muvaffaqiyatli login qildi"),
            token=token,
            user={
                "id": str(employee.id),
                "username": employee.username,
                "email": employee.email,
                "full_name": f"{employee.name} {employee.surname or ''}".strip(),
                "role": "employee",
                "salon_id": str(employee.salon_id) if employee.salon_id else None
            }
        )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Employee login xatosi: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("Server xatosi")
        )


@router.get("/admin/profile", response_model=AdminProfileResponse)
async def get_admin_profile(
    current_admin: Admin = Depends(get_current_admin),
    language: str = Depends(get_language)
):
    """
    Get admin profile endpoint
    """
    try:
        return AdminProfileResponse(
            id=str(current_admin.id),
            username=current_admin.username,
            email=current_admin.email,
            full_name=current_admin.full_name,
            role=current_admin.role,
            salon_id=str(current_admin.salon_id) if current_admin.salon_id else None,
            is_active=current_admin.is_active,
            created_at=current_admin.created_at.isoformat(),
            updated_at=current_admin.updated_at.isoformat()
        )

    except Exception as error:
        logger.error(f"Admin profile olish xatosi: {error}")
        # Simple translation function
        def t(key):
            translations = {
                "Server xatosi": {
                    "en": "Server error",
                    "uz": "Server xatosi", 
                    "ru": "Ошибка сервера"
                }
            }
            return translations.get(key, {}).get(language, key)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("Server xatosi")
        )