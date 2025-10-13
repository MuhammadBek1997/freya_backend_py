from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header,
    status,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Union
import os
import uuid
import hashlib
import secrets
import re
from datetime import datetime, timedelta
import httpx
from pathlib import Path
import json

from app.database import get_db
from app.i18nMini import get_translation
from app.models.user import User
from app.models.payment_card import PaymentCard
from app.models.salon import Salon
from app.models.employee import Employee
from app.models.user_employee_contact import UserEmployeeContact
from app.models.user_favourite_salon import UserFavouriteSalon
from app.schemas.salon import SalonResponse
from app.schemas.user import (
    UserRegistrationStep1,
    PhoneVerification,
    UserRegistrationStep2,
    UserLogin,
    PasswordResetRequest,
    PasswordReset,
    PhoneChangeRequest,
    UserUpdate,
    UserLocationUpdate,
    FavouriteSalonRequest,
    EmployeeContactRequest,
    PasswordChangeRequest,
    PaymentCardAdd,
    PaymentCardUpdate,
    UserResponse,
    UserLocationResponse,
    PaymentCardResponse,
    LoginResponse,
    TokenResponse,
    UserCityResponse,
    UserCityUpdate,
    UserAvatarUpdate
)
from app.schemas.employee import EmployeeResponse
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.auth.jwt_utils import JWTUtils
from app.config import settings

router = APIRouter(prefix="/api/users", tags=["Users"])


def generate_verification_code() -> str:
    """Generate 6-digit verification code"""
    code = str(secrets.randbelow(900000) + 100000)
    print(code)
    return code


def validate_phone_format(phone: str) -> bool:
    """Validate phone number format"""
    pattern = r"^\+998\d{9}$"
    return bool(re.match(pattern, phone))


def validate_email_format(email: str) -> bool:
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def luhn_check(card_number: str) -> bool:
    """Luhn algorithm for card number validation"""

    def digits_of(n):
        return [int(d) for d in str(n)]

    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0


def get_card_type(card_number: str) -> str:
    """Detect card type from card number"""
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


def mask_card_number(card_number: str) -> str:
    """Mask card number for display"""
    if len(card_number) < 4:
        return card_number
    return "*" * (len(card_number) - 4) + card_number[-4:]


async def send_sms_verification(
    phone: str, code: str, message_type: str = "verification"
):
    """Send SMS verification code using Eskiz service"""
    try:
        async with httpx.AsyncClient() as client:
            # Get token if needed
            if not settings.eskiz_token:
                auth_response = await client.post(
                    f"{settings.eskiz_base_url}/auth/login",
                    data={
                        "email": settings.eskiz_email,
                        "password": settings.eskiz_password,
                    },
                )
                print(
                    f"Auth response: {auth_response.status_code}, {auth_response.text}"
                )
                if auth_response.status_code == 200:
                    token_data = auth_response.json()
                    settings.eskiz_token = token_data.get("data", {}).get("token")

            # Send SMS
            headers = {"Authorization": f"Bearer {settings.eskiz_token}"}

            if message_type == "verification":
                message = f"Freya mobil ilovasiga ro'yxatdan o'tish uchun tasdiqlash kodi {code}"
            elif message_type == "password_reset":
                message = (
                    f"Freya ilovasida parolni tiklash uchun tasdiqlash kodi: {code}"
                )
            elif message_type == "phone_change":
                message = f"<#>Freya dasturiga Telefon raqamni o'zgartirish uchun tasdiqlash kodi: {code}"
            else:
                # message = f"Freya tasdiqlash kodi: {code}"
                return False
            if phone.startswith("+"):
                phone = phone[1:]
            sms_response = await client.post(
                f"{settings.eskiz_base_url}/message/sms/send",
                headers=headers,
                data={"mobile_phone": phone, "message": message, "from": "4546"},
            )
            print(f"SMS response: {sms_response.status_code}, {sms_response.text}")
            # print(f"SMS yuborildi: {sms_response.status_code}")
            return sms_response.status_code == 200
    except Exception as e:
        print(f"SMS yuborishda xatolik: {e}")
        return False


@router.post("/register/step1", response_model=dict)
async def register_step1(
    user_data: UserRegistrationStep1,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Ro'yxatdan o'tish - 1-qadam: Telefon va parol
    """
    # Check if phone already exists
    existing_user = db.query(User).filter(User.phone == user_data.phone).first()

    if existing_user and existing_user.is_verified and existing_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "auth.phoneExists"),
        )

    # Generate verification code
    verification_code = generate_verification_code()

    # Send SMS verification
    sms_sent = await send_sms_verification(user_data.phone, verification_code)
    if not sms_sent:
        return {
            "success": False,
            "message": get_translation(language, "auth.codeNotsent"),
            "sms_sent": sms_sent,
        }
    # Create temporary user record
    hashed_password = JWTUtils.hash_password(user_data.password)
    temp_user = User(
        phone=user_data.phone,
        password_hash=hashed_password,
        verification_code=verification_code,
        verification_expires_at=datetime.utcnow() + timedelta(minutes=5),
        is_verified=False,
        is_active=False,
    )
    db.add(temp_user)
    db.commit()

    return {
        "success": True,
        "message": get_translation(language, "auth.verificationCodeSent"),
        "sms_sent": sms_sent,
    }


@router.post("/verify-phone", response_model=dict)
async def verify_phone(
    verification_data: PhoneVerification,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Telefon raqamni tasdiqlash
    """
    user = db.query(User).filter(User.phone == verification_data.phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "auth.userNotFound"),
        )

    # Check verification code
    if (
        user.verification_code != verification_data.verification_code
        or user.verification_expires_at < datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "auth.invalidVerificationCode"),
        )

    # Mark phone as verified
    user.is_verified = True
    user.is_active = True
    user.verification_code = None
    user.verification_expires_at = None
    db.commit()

    return {"success": True, "message": get_translation(language, "auth.userVerified")}


@router.post("/register/step2", response_model=UserResponse)
async def register_step2(
    user_data: UserRegistrationStep2,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Ro'yxatdan o'tish - 2-qadam: Username va email
    """
    user = db.query(User).filter(User.phone == user_data.phone).first()
    if not user or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "auth.inactiveUser"),
        )

    # Check if username already exists
    existing_username = (
        db.query(User).filter(User.username == user_data.username).first()
    )
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "auth.userExists"),
        )

    # Update user with additional info
    user.username = user_data.username
    user.email = user_data.email
    user.is_active = True
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=LoginResponse)
async def login_user(
    login_data: UserLogin,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchi tizimga kirishi
    """
    user = db.query(User).filter(User.phone == login_data.phone).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_translation(language, "auth.invalidCredentials"),
        )

    if not JWTUtils.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_translation(language, "auth.invalidCredentials"),
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create access token
    access_token = JWTUtils.create_access_token(
        data={"id": str(user.id), "role": "user"}
    )

    return LoginResponse(
        success=True,
        message=get_translation(language, "auth.success"),
        token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/password/change", response_model=dict)
async def change_password(
    change_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchi parolini yangilash: eski parolni tekshirib, yangisini saqlash
    """
    # Verify old password
    # if not JWTUtils.verify_password(change_data.old_password, current_user.password_hash):
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=get_translation(language, "auth.invalidCredentials"),
    #     )

    # Update to new password
    current_user.password_hash = JWTUtils.hash_password(change_data.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": get_translation(language, "auth.success")}


@router.post("/password-reset/send-code", response_model=dict)
async def send_password_reset_code(
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Parolni tiklash uchun kod yuborish
    """
    user = db.query(User).filter(User.phone == reset_request.phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "auth.userNotFound"),
        )

    # Generate verification code
    verification_code = generate_verification_code()
    user.verification_code = verification_code
    user.verification_expires_at = datetime.utcnow() + timedelta(minutes=5)

    db.commit()

    # Send SMS
    sms_sent = await send_sms_verification(
        reset_request.phone, verification_code, "password_reset"
    )

    return {
        "success": True,
        "message": get_translation(language, "auth.verificationCodeSent"),
        "sms_sent": sms_sent,
    }


@router.post("/reset-password", response_model=dict)
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Parolni tiklash
    """
    user = db.query(User).filter(User.phone == reset_data.phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "auth.userNotFound"),
        )

    # Check verification code
    if (
        user.verification_code != reset_data.verification_code
        or user.verification_expires_at < datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "auth.invalidVerificationCode"),
        )

    # Update password
    user.password_hash = JWTUtils.hash_password(reset_data.new_password)
    user.verification_code = None
    user.verification_expires_at = None
    user.updated_at = datetime.utcnow()

    db.commit()

    return {"success": True, "message": get_translation(language, "auth.passwordReset")}


@router.post("/phone-change/send-code", response_model=dict)
async def send_phone_change_code(
    phone_request: PhoneChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Telefon raqamni o'zgartirish uchun kod yuborish
    """
    # Check if new phone already exists
    existing_user = db.query(User).filter(User.phone == phone_request.phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "auth.phoneExists"),
        )

    # Generate verification code
    verification_code = generate_verification_code()
    current_user.verification_code = verification_code
    current_user.verification_expires_at = datetime.utcnow() + timedelta(minutes=5)

    db.commit()

    # Send SMS to new phone
    sms_sent = await send_sms_verification(
        phone_request.phone, verification_code, "phone_change"
    )

    return {
        "success": True,
        "message": get_translation(language, "auth.verificationCodeSent"),
        "sms_sent": sms_sent,
    }


@router.post("/phone-change/verify", response_model=dict)
async def verify_phone_change(
    verification_data: PhoneVerification,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Telefon raqamni o'zgartirishni tasdiqlash
    """
    if (
        current_user.verification_code != verification_data.verification_code
        or current_user.verification_expires_at < datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "auth.codeExpired"),
        )

    # Check if new phone already exists
    existing_user = db.query(User).filter(User.phone == verification_data.phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "auth.phoneExists"),
        )

    # Update phone number
    current_user.phone = verification_data.phone
    current_user.verification_code = None
    current_user.verification_expires_at = None

    db.commit()

    return {"success": True, "message": get_translation(language, "auth.userUpdated")}


@router.delete("/delete", response_model=dict)
async def delete_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchi hisobini o'chirish
    """
    # Delete related data
    db.query(PaymentCard).filter(PaymentCard.user_id == current_user.id).delete()

    # Delete user
    db.delete(current_user)
    db.commit()

    return {"success": True, "message": get_translation(language, "auth.userDeleted")}


@router.put("/update", response_model=UserResponse)
async def update_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchi ma'lumotlarini yangilash
    """
    # Check if username already exists (if being updated)
    if user_update.username and user_update.username != current_user.username:
        existing_username = (
            db.query(User).filter(User.username == user_update.username).first()
        )
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_translation(language, "auth.userExists"),
            )

    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/generate-token", response_model=TokenResponse)
async def generate_user_token(
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Yangi token yaratish
    """
    access_token = JWTUtils.create_access_token(
        data={"id": str(current_user.id), "role": "user"}
    )

    return TokenResponse(
        success=True, message=get_translation(language, "success"), token=access_token
    )


@router.put("/location", response_model=UserLocationResponse)
async def update_user_location(
    location_data: UserLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchi joylashuvini yangilash
    """
    # Update user location fields directly
    current_user.latitude = location_data.latitude
    current_user.longitude = location_data.longitude
    current_user.address = location_data.address
    current_user.location_updated_at = datetime.utcnow()

    db.commit()
    db.refresh(current_user)

    return {
        "latitude": current_user.latitude,
        "longitude": current_user.longitude,
        "address": current_user.address,
        "location_updated_at": current_user.location_updated_at,
    }


@router.get("/location", response_model=UserLocationResponse)
async def get_user_location(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchi joylashuvini olish
    """
    if not current_user.latitude or not current_user.longitude:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    return {
        "latitude": current_user.latitude,
        "longitude": current_user.longitude,
        "address": current_user.address,
        "location_updated_at": current_user.location_updated_at,
    }


@router.get("/city", response_model=UserCityResponse)
async def get_user_city(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchi tanlagan shaharni olish (agar bo'lmasa None)
    """
    return {"city": current_user.city, "city_id": current_user.city_id}


@router.put("/city", response_model=UserCityResponse)
async def update_user_city(
    request: UserCityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchining shahrini city_id orqali yangilash
    """
    district = next(
        (
            d
            for d in _districts
            if d.get("id") is not None and int(d.get("id")) == request.city_id
        ),
        None,
    )
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    current_user.city = _name_by_lang(district, (language or "uz"))
    current_user.city_id = request.city_id
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return {"city": current_user.city, "city_id": current_user.city_id}


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchi profilini olish
    """
    return current_user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Token yuborilganda joriy foydalanuvchi maʼlumotlarini qaytarish"""
    return current_user


@router.post("/profile/image/upload", response_model=dict)
async def upload_profile_image(
    payload: UserAvatarUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Profil rasmini URL orqali yuklash (avatar_url). Faqat foydalanuvchi (user)lar uchun.
    """
    try:
        # Faqat userlar uchun ruxsat
        if getattr(current_user, "role", None) != "user":
            raise HTTPException(status_code=403, detail=get_translation(language, "errors.403"))

        # Foydalanuvchi avatarini yangilash
        current_user.avatar_url = payload.avatar_url.strip()
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)

        return {
            "success": True,
            "message": get_translation(language, "success"),
            "avatar_url": current_user.avatar_url,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @router.get("/profile/image")
# async def get_profile_image(current_user: User = Depends(get_current_user)):
#     """
#     Profil rasmini olish
#     """
#     if not current_user.avatar_url:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Profil rasmi topilmadi"
#         )

#     file_path = os.path.join(
#         settings.upload_path, current_user.avatar_url
#     )
#     print(f"Rasm fayli yo'li: {file_path}")
#     if not os.path.exists(file_path):
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Rasm fayli topilmadi"
#         )

#     return FileResponse(file_path)


@router.delete("/profile/image", response_model=dict)
async def delete_profile_image(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Profil rasmini o'chirish
    """
    if not current_user.avatar_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    # Delete file

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_DIR = os.path.join(BASE_DIR, settings.upload_path, "avatars")

    filename = current_user.avatar_url.split("/")[-1]
    file_path = (
        os.path.join(UPLOAD_DIR, filename).replace("\\", "/").replace("/app/", "/")
    )
    print(f"Rasm fayli yo'li: {file_path}")
    if os.path.exists(file_path):
        os.remove(file_path)

    # Update user
    current_user.avatar_url = None
    current_user.updated_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": get_translation(language, "success")}


@router.post("/favourites/add", response_model=dict)
async def add_favourite_salon(
    favourite_data: FavouriteSalonRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Sevimli salonga qo'shish
    """
    # Check if salon exists
    salon = db.query(Salon).filter(Salon.id == favourite_data.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    # Check if already in favourites
    existing_favourite = (
        db.query(UserFavouriteSalon)
        .filter(
            UserFavouriteSalon.user_id == current_user.id,
            UserFavouriteSalon.salon_id == favourite_data.salon_id,
        )
        .first()
    )

    if existing_favourite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "auth.userExists"),
        )

    # Add to favourites
    favourite = UserFavouriteSalon(
        user_id=current_user.id,
        salon_id=favourite_data.salon_id,
        created_at=datetime.utcnow(),
    )

    db.add(favourite)
    db.commit()

    return {"success": True, "message": get_translation(language, "success")}


@router.post("/favourites/remove", response_model=dict)
async def remove_favourite_salon(
    favourite_data: FavouriteSalonRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Sevimli salondan olib tashlash
    """
    favourite = (
        db.query(UserFavouriteSalon)
        .filter(
            UserFavouriteSalon.user_id == current_user.id,
            UserFavouriteSalon.salon_id == favourite_data.salon_id,
        )
        .first()
    )

    if not favourite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    db.delete(favourite)
    db.commit()

    return {"success": True, "message": get_translation(language, "success")}


@router.get("/favourites", response_model=List[SalonResponse])
async def get_favourite_salons(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Sevimli salonlar ro'yxatini olish
    """
    favourites = (
        db.query(UserFavouriteSalon)
        .filter(UserFavouriteSalon.user_id == current_user.id)
        .all()
    )

    salon_ids = [fav.salon_id for fav in favourites]
    salons = db.query(Salon).filter(Salon.id.in_(salon_ids)).all()

    return [
        {
            "id": salon.id,
            "name": salon.salon_name,
            "location": salon.location,
            "address_uz": salon.address_uz,
            "address_ru": salon.address_ru,
            "address_en": salon.address_en,
            "orientation_uz": salon.orientation_uz,
            "orientation_ru": salon.orientation_ru,
            "orientation_en": salon.orientation_en,
            "description_uz": salon.description_uz,
            "description_ru": salon.description_ru,
            "description_en": salon.description_en,
            "phone": salon.salon_phone,
            "rating": salon.salon_rating,
            "image_url": salon.salon_phone,
            "added_at": next(
                fav.created_at for fav in favourites if fav.salon_id == salon.id
            ),
        }
        for salon in salons
    ]


# Employee contacts endpoints
@router.post("/contacts/employees/add", response_model=dict)
async def add_employee_contact(
    contact_data: EmployeeContactRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchi uchun xodimni (employee) kontaktlarga qo'shish
    """
    # Check if employee exists and active
    employee = (
        db.query(Employee)
        .filter(Employee.id == contact_data.employee_id, Employee.is_active == True)
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    # Check if already in contacts
    existing_contact = (
        db.query(UserEmployeeContact)
        .filter(
            UserEmployeeContact.user_id == current_user.id,
            UserEmployeeContact.employee_id == contact_data.employee_id,
        )
        .first()
    )
    if existing_contact:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "auth.userExists"),
        )

    # Add to contacts
    contact = UserEmployeeContact(
        user_id=current_user.id,
        employee_id=contact_data.employee_id,
        created_at=datetime.utcnow(),
    )
    db.add(contact)
    db.commit()

    return {"success": True, "message": get_translation(language, "success")}


@router.post("/contacts/employees/remove", response_model=dict)
async def remove_employee_contact(
    contact_data: EmployeeContactRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchi kontaktlaridan xodimni olib tashlash
    """
    contact = (
        db.query(UserEmployeeContact)
        .filter(
            UserEmployeeContact.user_id == current_user.id,
            UserEmployeeContact.employee_id == contact_data.employee_id,
        )
        .first()
    )
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation(language, "errors.404"),
        )

    db.delete(contact)
    db.commit()

    return {"success": True, "message": get_translation(language, "success")}


@router.get("/contacts/employees", response_model=List[EmployeeResponse])
async def get_employee_contacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    Foydalanuvchi kontaktlaridagi xodimlar ro'yxatini olish
    """
    contacts = (
        db.query(UserEmployeeContact)
        .filter(UserEmployeeContact.user_id == current_user.id)
        .all()
    )
    employee_ids = [c.employee_id for c in contacts]
    if not employee_ids:
        return []

    employees = db.query(Employee).filter(Employee.id.in_(employee_ids)).all()

    # Map to response format
    return [
        {
            "id": emp.id,
            "salon_id": emp.salon_id,
            "name": emp.name,
            "surname": emp.surname,
            "phone": emp.phone,
            "email": emp.email,
            "role": emp.role,
            "username": emp.username,
            "profession": emp.profession,
            "bio": emp.bio,
            "specialization": emp.specialization,
            "avatar_url": emp.avatar_url,
            "is_active": emp.is_active,
            "is_waiting": emp.is_waiting,
            "created_at": emp.created_at,
            "updated_at": emp.updated_at,
            "deleted_at": emp.deleted_at,
            "salon_name": emp.salon.salon_name if emp.salon else None,
        }
        for emp in employees
    ]


@router.post("/payment-cards", response_model=PaymentCardResponse)
async def add_payment_card(
    card_data: PaymentCardAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    To'lov kartasini qo'shish
    """
    # Validate card number using Luhn algorithm
    if not luhn_check(card_data.card_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=get_translation(language, "errors.400")
        )

    # Check if card already exists
    existing_card = (
        db.query(PaymentCard)
        .filter(
            PaymentCard.user_id == current_user.id,
            PaymentCard.card_number_hash
            == hashlib.sha256(card_data.card_number.encode()).hexdigest(),
        )
        .first()
    )

    if existing_card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation(language, "auth.userExists"),
        )

    # If this is the first card or set as default, make it default
    if card_data.is_default:
        # Remove default from other cards
        db.query(PaymentCard).filter(PaymentCard.user_id == current_user.id).update(
            {"is_default": False}
        )

    # Check if user has no cards, make this default
    user_cards_count = (
        db.query(PaymentCard).filter(PaymentCard.user_id == current_user.id).count()
    )

    if user_cards_count == 0:
        card_data.is_default = True

    # Create payment card
    payment_card = PaymentCard(
        user_id=current_user.id,
        card_number_hash=hashlib.sha256(card_data.card_number.encode()).hexdigest(),
        masked_card_number=mask_card_number(card_data.card_number),
        card_type=get_card_type(card_data.card_number),
        card_holder_name=card_data.card_holder_name,
        expiry_month=card_data.expiry_month,
        expiry_year=card_data.expiry_year,
        is_default=card_data.is_default,
        created_at=datetime.utcnow(),
    )

    db.add(payment_card)
    db.commit()
    db.refresh(payment_card)

    return payment_card


@router.get("/payment-cards", response_model=List[PaymentCardResponse])
async def get_user_payment_cards(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),

):
    """
    Foydalanuvchi to'lov kartalari ro'yxatini olish
    """
    cards = (
        db.query(PaymentCard)
        .filter(PaymentCard.user_id == current_user.id)
        .order_by(PaymentCard.is_default.desc(), PaymentCard.created_at.desc())
        .all()
    )

    return cards


@router.put("/payment-cards/{card_id}", response_model=PaymentCardResponse)
async def update_payment_card(
    card_id: int,
    card_update: PaymentCardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    To'lov kartasini yangilash
    """
    card = (
        db.query(PaymentCard)
        .filter(PaymentCard.id == card_id, PaymentCard.user_id == current_user.id)
        .first()
    )

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"),
        )

    # If setting as default, remove default from other cards
    if card_update.is_default:
        db.query(PaymentCard).filter(
            PaymentCard.user_id == current_user.id, PaymentCard.id != card_id
        ).update({"is_default": False})

    # Update fields
    update_data = card_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(card, field, value)

    db.commit()
    db.refresh(card)

    return card


@router.delete("/payment-cards/{card_id}", response_model=dict)
async def delete_payment_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    To'lov kartasini o'chirish
    """
    card = (
        db.query(PaymentCard)
        .filter(PaymentCard.id == card_id, PaymentCard.user_id == current_user.id)
        .first()
    )

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"),
        )

    was_default = card.is_default
    db.delete(card)

    # If deleted card was default, make another card default
    if was_default:
        remaining_card = (
            db.query(PaymentCard).filter(PaymentCard.user_id == current_user.id).first()
        )
        if remaining_card:
            remaining_card.is_default = True

    db.commit()

    return {"success": True, "message": get_translation(language, "success")}


@router.put("/payment-cards/{card_id}/set-default", response_model=PaymentCardResponse)
async def set_default_payment_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """
    To'lov kartasini asosiy qilib belgilash
    """
    card = (
        db.query(PaymentCard)
        .filter(PaymentCard.id == card_id, PaymentCard.user_id == current_user.id)
        .first()
    )

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=get_translation(language, "errors.404"),
        )

    # Remove default from all cards
    db.query(PaymentCard).filter(PaymentCard.user_id == current_user.id).update(
        {"is_default": False}
    )

    # Set this card as default
    card.is_default = True
    db.commit()
    db.refresh(card)

    return card
"""
City dataset (districts) loader for user city selection
"""
CITY_DATA_PATH = Path(__file__).resolve().parents[2] / "city.json"
_districts = []
try:
    with CITY_DATA_PATH.open("r", encoding="utf-8") as f:
        _city_data = json.load(f)
        _districts = _city_data.get("districts", [])
except Exception:
    _districts = []


def _name_by_lang(item: dict, lang: str) -> str:
    lang = (lang or "uz").lower()
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    return item.get(lang) or item.get("uz") or ""
