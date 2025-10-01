from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import hashlib
import secrets
import re
from datetime import datetime, timedelta
import httpx

from app.database import get_db
from app.models.user import User
from app.models.payment_card import PaymentCard
from app.models.salon import Salon
from app.models.user_favourite_salon import UserFavouriteSalon
from app.schemas.user import (
    UserRegistrationStep1, PhoneVerification, UserRegistrationStep2,
    UserLogin, PasswordResetRequest, PasswordReset, PhoneChangeRequest,
    UserUpdate, UserLocationUpdate, FavouriteSalonRequest,
    PaymentCardAdd, PaymentCardUpdate,
    UserResponse, UserLocationResponse, PaymentCardResponse,
    LoginResponse, TokenResponse
)
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.auth.jwt_utils import JWTUtils
from app.config import settings

router = APIRouter(prefix="/api/users", tags=["Users"])


def generate_verification_code() -> str:
    """Generate 6-digit verification code"""
    return str(secrets.randbelow(900000) + 100000)


def validate_phone_format(phone: str) -> bool:
    """Validate phone number format"""
    pattern = r'^\+998\d{9}$'
    return bool(re.match(pattern, phone))


def validate_email_format(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
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
        checksum += sum(digits_of(d*2))
    return checksum % 10 == 0


def get_card_type(card_number: str) -> str:
    """Detect card type from card number"""
    if card_number.startswith('4'):
        return 'Visa'
    elif card_number.startswith(('51', '52', '53', '54', '55')):
        return 'MasterCard'
    elif card_number.startswith('9860'):
        return 'Uzcard'
    elif card_number.startswith('8600'):
        return 'Humo'
    else:
        return 'Unknown'


def mask_card_number(card_number: str) -> str:
    """Mask card number for display"""
    if len(card_number) < 4:
        return card_number
    return '*' * (len(card_number) - 4) + card_number[-4:]


async def send_sms_verification(phone: str, code: str, message_type: str = "verification"):
    """Send SMS verification code using Eskiz service"""
    try:
        async with httpx.AsyncClient() as client:
            # Get token if needed
            if not settings.ESKIZ_TOKEN:
                auth_response = await client.post(
                    f"{settings.ESKIZ_BASE_URL}/auth/login",
                    data={
                        "email": settings.ESKIZ_EMAIL,
                        "password": settings.ESKIZ_PASSWORD
                    }
                )
                if auth_response.status_code == 200:
                    token_data = auth_response.json()
                    settings.ESKIZ_TOKEN = token_data.get("data", {}).get("token")
            
            # Send SMS
            headers = {"Authorization": f"Bearer {settings.ESKIZ_TOKEN}"}
            
            if message_type == "verification":
                message = f"Freya ilovasiga kirish uchun tasdiqlash kodi: {code}"
            elif message_type == "password_reset":
                message = f"Freya ilovasida parolni tiklash kodi: {code}"
            elif message_type == "phone_change":
                message = f"Freya ilovasida telefon raqamni o'zgartirish kodi: {code}"
            else:
                message = f"Freya tasdiqlash kodi: {code}"
            
            sms_response = await client.post(
                f"{settings.ESKIZ_BASE_URL}/message/sms/send",
                headers=headers,
                data={
                    "mobile_phone": phone,
                    "message": message,
                    "from": "4546"
                }
            )
            
            return sms_response.status_code == 200
    except Exception as e:
        print(f"SMS yuborishda xatolik: {e}")
        return False


@router.post("/register/step1", response_model=dict)
async def register_step1(
    user_data: UserRegistrationStep1,
    db: Session = Depends(get_db)
):
    """
    Ro'yxatdan o'tish - 1-qadam: Telefon va parol
    """
    # Check if phone already exists
    existing_user = db.query(User).filter(User.phone == user_data.phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu telefon raqam allaqachon ro'yxatdan o'tgan"
        )
    
    # Generate verification code
    verification_code = generate_verification_code()
    
    # Create temporary user record
    hashed_password = JWTUtils.hash_password(user_data.password)
    temp_user = User(
        phone=user_data.phone,
        password_hash=hashed_password,
        verification_code=verification_code,
        verification_expires_at=datetime.utcnow() + timedelta(minutes=5),
        is_verified=False,
        is_active=False
    )
    
    db.add(temp_user)
    db.commit()
    
    # Send SMS verification
    sms_sent = await send_sms_verification(user_data.phone, verification_code)
    
    return {
        "success": True,
        "message": "Tasdiqlash kodi yuborildi",
        "sms_sent": sms_sent
    }


@router.post("/verify-phone", response_model=dict)
async def verify_phone(
    verification_data: PhoneVerification,
    db: Session = Depends(get_db)
):
    """
    Telefon raqamni tasdiqlash
    """
    user = db.query(User).filter(User.phone == verification_data.phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi"
        )
    
    # Check verification code
    if (user.verification_code != verification_data.verification_code or
        user.verification_expires_at < datetime.utcnow()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tasdiqlash kodi noto'g'ri yoki muddati tugagan"
        )
    
    # Mark phone as verified
    user.is_verified = True
    user.is_active = True
    user.verification_code = None
    user.verification_expires_at = None
    db.commit()
    
    return {
        "success": True,
        "message": "Telefon raqam tasdiqlandi"
    }


@router.post("/register/step2", response_model=UserResponse)
async def register_step2(
    user_data: UserRegistrationStep2,
    db: Session = Depends(get_db)
):
    """
    Ro'yxatdan o'tish - 2-qadam: Username va email
    """
    user = db.query(User).filter(User.phone == user_data.phone).first()
    if not user or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telefon raqam tasdiqlanmagan"
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu username allaqachon band"
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
    db: Session = Depends(get_db)
):
    """
    Foydalanuvchi tizimga kirishi
    """
    user = db.query(User).filter(User.phone == login_data.phone).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telefon raqam yoki parol noto'g'ri"
        )
    
    if not JWTUtils.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telefon raqam yoki parol noto'g'ri"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token = JWTUtils.create_access_token(data={"id": str(user.id), "role": "user"})
    
    return LoginResponse(
        success=True,
        message="Muvaffaqiyatli kirildi",
        token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/password-reset/send-code", response_model=dict)
async def send_password_reset_code(
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Parolni tiklash uchun kod yuborish
    """
    user = db.query(User).filter(User.phone == reset_request.phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu telefon raqam bilan foydalanuvchi topilmadi"
        )
    
    # Generate verification code
    verification_code = generate_verification_code()
    user.verification_code = verification_code
    user.verification_expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    db.commit()
    
    # Send SMS
    sms_sent = await send_sms_verification(reset_request.phone, verification_code, "password_reset")
    
    return {
        "success": True,
        "message": "Parolni tiklash kodi yuborildi",
        "sms_sent": sms_sent
    }


@router.post("/reset-password", response_model=dict)
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Parolni tiklash
    """
    user = db.query(User).filter(User.phone == reset_data.phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi"
        )
    
    # Check verification code
    if (user.verification_code != reset_data.verification_code or
        user.verification_expires_at < datetime.utcnow()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tasdiqlash kodi noto'g'ri yoki muddati tugagan"
        )
    
    # Update password
    user.password_hash = JWTUtils.hash_password(reset_data.new_password)
    user.verification_code = None
    user.verification_expires_at = None
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Parol muvaffaqiyatli o'zgartirildi"
    }


@router.post("/phone-change/send-code", response_model=dict)
async def send_phone_change_code(
    phone_request: PhoneChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Telefon raqamni o'zgartirish uchun kod yuborish
    """
    # Check if new phone already exists
    existing_user = db.query(User).filter(User.phone == phone_request.phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu telefon raqam allaqachon ishlatilmoqda"
        )
    
    # Generate verification code
    verification_code = generate_verification_code()
    current_user.verification_code = verification_code
    current_user.verification_code_expires = datetime.utcnow() + timedelta(minutes=5)
    current_user.new_phone = phone_request.phone
    
    db.commit()
    
    # Send SMS to new phone
    sms_sent = await send_sms_verification(phone_request.phone, verification_code, "phone_change")
    
    return {
        "success": True,
        "message": "Yangi telefon raqamga tasdiqlash kodi yuborildi",
        "sms_sent": sms_sent
    }


@router.delete("/delete", response_model=dict)
async def delete_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Foydalanuvchi hisobini o'chirish
    """
    # Delete related data
    db.query(PaymentCard).filter(PaymentCard.user_id == current_user.id).delete()
    
    # Delete user
    db.delete(current_user)
    db.commit()
    
    return {
        "success": True,
        "message": "Hisob muvaffaqiyatli o'chirildi"
    }


@router.put("/update", response_model=UserResponse)
async def update_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Foydalanuvchi ma'lumotlarini yangilash
    """
    # Check if username already exists (if being updated)
    if user_update.username and user_update.username != current_user.username:
        existing_username = db.query(User).filter(User.username == user_update.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu username allaqachon band"
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
    current_user: User = Depends(get_current_user)
):
    """
    Yangi token yaratish
    """
    access_token = JWTUtils.create_access_token(data={"id": current_user.id, "role": "user"})
    
    return TokenResponse(
        success=True,
        message="Yangi token yaratildi",
        token=access_token
    )


@router.put("/location", response_model=UserLocationResponse)
async def update_user_location(
    location_data: UserLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
        "location_updated_at": current_user.location_updated_at
    }


@router.get("/location", response_model=UserLocationResponse)
async def get_user_location(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Foydalanuvchi joylashuvini olish
    """
    if not current_user.latitude or not current_user.longitude:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi joylashuvi topilmadi"
        )
    
    return {
        "latitude": current_user.latitude,
        "longitude": current_user.longitude,
        "address": current_user.address,
        "location_updated_at": current_user.location_updated_at
    }


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Foydalanuvchi profilini olish
    """
    return current_user


@router.post("/profile/image/upload", response_model=dict)
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Profil rasmini yuklash
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faqat rasm fayllari qabul qilinadi"
        )
    
    # Create uploads directory if not exists
    upload_dir = os.path.join(settings.UPLOAD_PATH, "avatars")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{current_user.id}_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Update user avatar URL
    current_user.avatar_url = f"/uploads/avatars/{filename}"
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Profil rasmi yuklandi",
        "avatar_url": current_user.avatar_url
    }


@router.get("/profile/image")
async def get_profile_image(
    current_user: User = Depends(get_current_user)
):
    """
    Profil rasmini olish
    """
    if not current_user.avatar_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil rasmi topilmadi"
        )
    
    file_path = os.path.join(settings.UPLOAD_PATH, current_user.avatar_url.lstrip('/uploads/'))
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rasm fayli topilmadi"
        )
    
    return FileResponse(file_path)


@router.delete("/profile/image", response_model=dict)
async def delete_profile_image(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Profil rasmini o'chirish
    """
    if not current_user.avatar_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil rasmi topilmadi"
        )
    
    # Delete file
    file_path = os.path.join(settings.UPLOAD_PATH, current_user.avatar_url.lstrip('/uploads/'))
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Update user
    current_user.avatar_url = None
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Profil rasmi o'chirildi"
    }


@router.post("/favourites/add", response_model=dict)
async def add_favourite_salon(
    favourite_data: FavouriteSalonRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sevimli salonga qo'shish
    """
    # Check if salon exists
    salon = db.query(Salon).filter(Salon.id == favourite_data.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon topilmadi"
        )
    
    # Check if already in favourites
    existing_favourite = db.query(UserFavouriteSalon).filter(
        UserFavouriteSalon.user_id == current_user.id,
        UserFavouriteSalon.salon_id == favourite_data.salon_id
    ).first()
    
    if existing_favourite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salon allaqachon sevimlilar ro'yxatida"
        )
    
    # Add to favourites
    favourite = UserFavouriteSalon(
        user_id=current_user.id,
        salon_id=favourite_data.salon_id,
        created_at=datetime.utcnow()
    )
    
    db.add(favourite)
    db.commit()
    
    return {
        "success": True,
        "message": "Salon sevimlilar ro'yxatiga qo'shildi"
    }


@router.post("/favourites/remove", response_model=dict)
async def remove_favourite_salon(
    favourite_data: FavouriteSalonRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sevimli salondan olib tashlash
    """
    favourite = db.query(UserFavouriteSalon).filter(
        UserFavouriteSalon.user_id == current_user.id,
        UserFavouriteSalon.salon_id == favourite_data.salon_id
    ).first()
    
    if not favourite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon sevimlilar ro'yxatida topilmadi"
        )
    
    db.delete(favourite)
    db.commit()
    
    return {
        "success": True,
        "message": "Salon sevimlilar ro'yxatidan olib tashlandi"
    }


@router.get("/favourites", response_model=List[dict])
async def get_favourite_salons(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sevimli salonlar ro'yxatini olish
    """
    favourites = db.query(UserFavouriteSalon).filter(
        UserFavouriteSalon.user_id == current_user.id
    ).all()
    
    salon_ids = [fav.salon_id for fav in favourites]
    salons = db.query(Salon).filter(Salon.id.in_(salon_ids)).all()
    
    return [
        {
            "id": salon.id,
            "name": salon.name,
            "address": salon.address,
            "phone": salon.phone,
            "rating": salon.rating,
            "image_url": salon.image_url,
            "added_at": next(fav.created_at for fav in favourites if fav.salon_id == salon.id)
        }
        for salon in salons
    ]


@router.post("/payment-cards", response_model=PaymentCardResponse)
async def add_payment_card(
    card_data: PaymentCardAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    To'lov kartasini qo'shish
    """
    # Validate card number using Luhn algorithm
    if not luhn_check(card_data.card_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Karta raqami noto'g'ri"
        )
    
    # Check if card already exists
    existing_card = db.query(PaymentCard).filter(
        PaymentCard.user_id == current_user.id,
        PaymentCard.card_number_hash == hashlib.sha256(card_data.card_number.encode()).hexdigest()
    ).first()
    
    if existing_card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu karta allaqachon qo'shilgan"
        )
    
    # If this is the first card or set as default, make it default
    if card_data.is_default:
        # Remove default from other cards
        db.query(PaymentCard).filter(
            PaymentCard.user_id == current_user.id
        ).update({"is_default": False})
    
    # Check if user has no cards, make this default
    user_cards_count = db.query(PaymentCard).filter(
        PaymentCard.user_id == current_user.id
    ).count()
    
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
        created_at=datetime.utcnow()
    )
    
    db.add(payment_card)
    db.commit()
    db.refresh(payment_card)
    
    return payment_card


@router.get("/payment-cards", response_model=List[PaymentCardResponse])
async def get_user_payment_cards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Foydalanuvchi to'lov kartalari ro'yxatini olish
    """
    cards = db.query(PaymentCard).filter(
        PaymentCard.user_id == current_user.id
    ).order_by(PaymentCard.is_default.desc(), PaymentCard.created_at.desc()).all()
    
    return cards


@router.put("/payment-cards/{card_id}", response_model=PaymentCardResponse)
async def update_payment_card(
    card_id: int,
    card_update: PaymentCardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    To'lov kartasini yangilash
    """
    card = db.query(PaymentCard).filter(
        PaymentCard.id == card_id,
        PaymentCard.user_id == current_user.id
    ).first()
    
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Karta topilmadi"
        )
    
    # If setting as default, remove default from other cards
    if card_update.is_default:
        db.query(PaymentCard).filter(
            PaymentCard.user_id == current_user.id,
            PaymentCard.id != card_id
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
    db: Session = Depends(get_db)
):
    """
    To'lov kartasini o'chirish
    """
    card = db.query(PaymentCard).filter(
        PaymentCard.id == card_id,
        PaymentCard.user_id == current_user.id
    ).first()
    
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Karta topilmadi"
        )
    
    was_default = card.is_default
    db.delete(card)
    
    # If deleted card was default, make another card default
    if was_default:
        remaining_card = db.query(PaymentCard).filter(
            PaymentCard.user_id == current_user.id
        ).first()
        if remaining_card:
            remaining_card.is_default = True
    
    db.commit()
    
    return {
        "success": True,
        "message": "Karta muvaffaqiyatli o'chirildi"
    }


@router.put("/payment-cards/{card_id}/set-default", response_model=PaymentCardResponse)
async def set_default_payment_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    To'lov kartasini asosiy qilib belgilash
    """
    card = db.query(PaymentCard).filter(
        PaymentCard.id == card_id,
        PaymentCard.user_id == current_user.id
    ).first()
    
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Karta topilmadi"
        )
    
    # Remove default from all cards
    db.query(PaymentCard).filter(
        PaymentCard.user_id == current_user.id
    ).update({"is_default": False})
    
    # Set this card as default
    card.is_default = True
    db.commit()
    db.refresh(card)
    
    return card