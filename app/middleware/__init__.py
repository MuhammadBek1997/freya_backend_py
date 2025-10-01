# Middleware module
from .cors import setup_cors
from .language import LanguageMiddleware, get_language, get_translation_function
from .validation import (
    ValidationUtils,
    validate_phone_number,
    validate_email,
    validate_password,
    validate_verification_code,
    validate_name,
    check_phone_exists,
    check_email_exists
)

__all__ = [
    'setup_cors',
    'LanguageMiddleware',
    'get_language',
    'get_translation_function',
    'ValidationUtils',
    'validate_phone_number',
    'validate_email',
    'validate_password',
    'validate_verification_code',
    'validate_name',
    'check_phone_exists',
    'check_email_exists'
]