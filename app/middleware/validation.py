"""
Validation middleware and utilities
"""
import re
from typing import Optional
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from app.models import User
from app.middleware.language import get_translation_function


class ValidationUtils:
    """Validation utility functions"""
    
    @staticmethod
    def validate_phone_format(phone: str) -> bool:
        """Validate Uzbek phone number format"""
        # Uzbek phone format: +998XXXXXXXXX
        phone_regex = r'^\+998[0-9]{9}$'
        return bool(re.match(phone_regex, phone))
    
    @staticmethod
    def validate_email_format(email: str) -> bool:
        """Validate email format"""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_regex, email))
    
    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """Validate password strength"""
        # At least 6 characters
        if len(password) < 6:
            return False
        return True
    
    @staticmethod
    def validate_verification_code(code: str) -> bool:
        """Validate verification code format"""
        # 6 digit code
        code_regex = r'^[0-9]{6}$'
        return bool(re.match(code_regex, code))
    
    @staticmethod
    def validate_name_format(name: str) -> bool:
        """Validate name format"""
        if not name or len(name.strip()) < 2:
            return False
        
        # Only letters, spaces, and some special characters
        name_regex = r'^[a-zA-ZА-Яа-яЁёўғҳқўзжчшъ\s\'-]{2,50}$'
        return bool(re.match(name_regex, name.strip()))


def validate_phone_number(request: Request, phone: str) -> str:
    """Validate phone number format"""
    t = get_translation_function(request)
    
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("phone.required")
        )
    
    if not ValidationUtils.validate_phone_format(phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("phone.invalid_format")
        )
    
    return phone.strip()


def validate_email(request: Request, email: str) -> str:
    """Validate email format"""
    t = get_translation_function(request)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    if not ValidationUtils.validate_email_format(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("email.invalid_format")
        )
    
    return email.strip().lower()


def validate_password(request: Request, password: str) -> str:
    """Validate password strength"""
    t = get_translation_function(request)
    
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required"
        )
    
    if not ValidationUtils.validate_password_strength(password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("password.too_weak")
        )
    
    return password


def validate_verification_code(request: Request, code: str) -> str:
    """Validate verification code"""
    t = get_translation_function(request)
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code is required"
        )
    
    if not ValidationUtils.validate_verification_code(code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code format"
        )
    
    return code


def validate_name(request: Request, name: str) -> str:
    """Validate name format"""
    t = get_translation_function(request)
    
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is required"
        )
    
    if not ValidationUtils.validate_name_format(name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid name format"
        )
    
    return name.strip()


def check_phone_exists(request: Request, db: Session, phone: str, exclude_user_id: Optional[str] = None) -> None:
    """Check if phone number already exists"""
    t = get_translation_function(request)
    
    query = db.query(User).filter(User.phone == phone)
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    
    existing_user = query.first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("phone.already_exists")
        )


def check_email_exists(request: Request, db: Session, email: str, exclude_user_id: Optional[str] = None) -> None:
    """Check if email already exists"""
    t = get_translation_function(request)
    
    query = db.query(User).filter(User.email == email)
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    
    existing_user = query.first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already registered"
        )