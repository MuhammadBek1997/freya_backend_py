"""
Language detection and localization middleware
"""
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import re


class LanguageMiddleware(BaseHTTPMiddleware):
    """Language detection middleware"""
    
    def __init__(self, app, default_language: str = "en"):
        super().__init__(app)
        self.default_language = default_language
        self.supported_languages = ["en", "uz", "ru"]
    
    async def dispatch(self, request: Request, call_next):
        # Detect language
        language = self._detect_language(request)
        
        # Set language in request state
        request.state.language = language
        
        # Process request
        response = await call_next(request)
        
        # Set language in response headers
        response.headers["Content-Language"] = language
        
        # Set language cookie if different from current
        current_cookie_lang = request.cookies.get("language")
        if language != current_cookie_lang:
            response.set_cookie(
                "language",
                language,
                max_age=365 * 24 * 60 * 60,  # 1 year
                httponly=False,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax"
            )
        
        return response
    
    def _detect_language(self, request: Request) -> str:
        """Detect user's preferred language"""
        
        # 1. Check query parameters
        for param in ["lang", "lng", "language"]:
            if param in request.query_params:
                lang = request.query_params[param]
                if lang in self.supported_languages:
                    return lang
        
        # 2. Check custom header
        x_language = request.headers.get("x-language")
        if x_language and x_language in self.supported_languages:
            return x_language
        
        # 3. Check Accept-Language header
        accept_language = request.headers.get("accept-language")
        if accept_language:
            lang = self._parse_accept_language(accept_language)
            if lang:
                return lang
        
        # 4. Check cookies
        cookie_lang = request.cookies.get("language")
        if cookie_lang and cookie_lang in self.supported_languages:
            return cookie_lang
        
        # 5. Default language
        return self.default_language
    
    def _parse_accept_language(self, accept_language: str) -> Optional[str]:
        """Parse Accept-Language header"""
        try:
            # Simple parsing of Accept-Language header
            # Format: en-US,en;q=0.9,uz;q=0.8,ru;q=0.7
            languages = []
            
            for lang_part in accept_language.split(","):
                lang_part = lang_part.strip()
                
                # Extract language code and quality
                if ";" in lang_part:
                    lang_code, quality_part = lang_part.split(";", 1)
                    quality_match = re.search(r"q=([0-9.]+)", quality_part)
                    quality = float(quality_match.group(1)) if quality_match else 1.0
                else:
                    lang_code = lang_part
                    quality = 1.0
                
                # Normalize language code
                lang_code = lang_code.strip().lower()
                if "-" in lang_code:
                    lang_code = lang_code.split("-")[0]
                
                # Map common language codes
                lang_map = {
                    "uz": "uz",
                    "ru": "ru", 
                    "en": "en"
                }
                
                normalized_lang = lang_map.get(lang_code, lang_code)
                if normalized_lang in self.supported_languages:
                    languages.append((normalized_lang, quality))
            
            # Sort by quality (highest first)
            languages.sort(key=lambda x: x[1], reverse=True)
            
            # Return the highest quality supported language
            if languages:
                return languages[0][0]
                
        except Exception:
            pass
        
        return None


def get_language(request: Request) -> str:
    """Get current language from request"""
    return getattr(request.state, "language", "en")


def get_translation_function(request: Request):
    """Get translation function for current language"""
    language = get_language(request)
    
    # Simple translation function (can be replaced with proper i18n)
    def translate(key: str, **kwargs) -> str:
        # This is a placeholder - in real implementation, 
        # you would load translations from files or database
        translations = {
            "en": {
                "success.general": "Success",
                "error.general": "An error occurred",
                "error.validation": "Validation error",
                "error.unauthorized": "Unauthorized",
                "error.forbidden": "Forbidden",
                "error.not_found": "Not found",
                "phone.required": "Phone number is required",
                "phone.invalid_format": "Invalid phone format. Correct format: +998XXXXXXXXX",
                "phone.already_exists": "This phone number is already registered",
                "email.invalid_format": "Invalid email format",
                "password.too_weak": "Password is too weak"
            },
            "uz": {
                "success.general": "Muvaffaqiyatli",
                "error.general": "Xatolik yuz berdi",
                "error.validation": "Validatsiya xatosi",
                "error.unauthorized": "Ruxsat berilmagan",
                "error.forbidden": "Taqiqlangan",
                "error.not_found": "Topilmadi",
                "phone.required": "Telefon raqam majburiy",
                "phone.invalid_format": "Telefon raqam formati noto'g'ri. To'g'ri format: +998XXXXXXXXX",
                "phone.already_exists": "Bu telefon raqam allaqachon ro'yxatdan o'tgan",
                "email.invalid_format": "Email formati noto'g'ri",
                "password.too_weak": "Parol juda zaif"
            },
            "ru": {
                "success.general": "Успешно",
                "error.general": "Произошла ошибка",
                "error.validation": "Ошибка валидации",
                "error.unauthorized": "Неавторизован",
                "error.forbidden": "Запрещено",
                "error.not_found": "Не найдено",
                "phone.required": "Номер телефона обязателен",
                "phone.invalid_format": "Неверный формат телефона. Правильный формат: +998XXXXXXXXX",
                "phone.already_exists": "Этот номер телефона уже зарегистрирован",
                "email.invalid_format": "Неверный формат email",
                "password.too_weak": "Пароль слишком слабый"
            }
        }
        
        lang_translations = translations.get(language, translations["en"])
        message = lang_translations.get(key, key)
        
        # Simple string formatting
        if kwargs:
            try:
                message = message.format(**kwargs)
            except (KeyError, ValueError):
                pass
        
        return message
    
    return translate