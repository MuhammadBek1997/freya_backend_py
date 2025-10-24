"""
Payment validation utilities
"""
import re
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.config import settings


class PaymentValidator:
    """To'lov ma'lumotlarini validatsiya qilish"""
    
    @staticmethod
    def validate_card_number(card_number: str) -> bool:
        """
        Karta raqamini Luhn algoritmi bilan tekshirish
        """
        # Faqat raqamlarni qoldirish
        card_number = re.sub(r'\D', '', card_number)
        
        # Uzunlik tekshiruvi
        if len(card_number) < 13 or len(card_number) > 19:
            return False
        
        # Luhn algoritmi
        def luhn_check(card_num):
            total = 0
            reverse_digits = card_num[::-1]
            
            for i, digit in enumerate(reverse_digits):
                n = int(digit)
                if i % 2 == 1:  # Har ikkinchi raqamni ikki baravarga ko'paytirish
                    n *= 2
                    if n > 9:
                        n = n // 10 + n % 10
                total += n
            
            return total % 10 == 0
        
        return luhn_check(card_number)
    
    @staticmethod
    def validate_expiry_date(month: int, year: int) -> bool:
        """
        Karta amal qilish muddatini tekshirish
        """
        if not (1 <= month <= 12):
            return False
        
        # Yil 2 yoki 4 raqamli bo'lishi mumkin
        if year < 100:
            year += 2000
        
        current_date = datetime.now()
        expiry_date = datetime(year, month, 1)
        
        # Karta amal qilish muddati o'tmagan bo'lishi kerak
        return expiry_date > current_date
    
    @staticmethod
    def validate_amount(amount: int, payment_type: str) -> bool:
        """
        To'lov miqdorini tekshirish
        """
        if amount <= 0:
            return False
        
        # Har xil to'lov turlari uchun minimal va maksimal miqdorlar
        limits = {
            "employee_post": {"min": 1000, "max": 1000000},  # 10 so'm - 10,000 so'm
            "user_premium": {"min": 5000, "max": 500000},    # 50 so'm - 5,000 so'm
            "salon_top": {"min": 10000, "max": 2000000}      # 100 so'm - 20,000 so'm
        }
        
        if payment_type not in limits:
            return False
        
        limit = limits[payment_type]
        return limit["min"] <= amount <= limit["max"]
    
    @staticmethod
    def validate_transaction_id(transaction_id: str) -> bool:
        """
        Transaction ID formatini tekshirish
        """
        # Transaction ID UUID formatida bo'lishi kerak
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, transaction_id, re.IGNORECASE))
    
    @staticmethod
    def validate_click_signature(params: Dict[str, Any], received_signature: str) -> bool:
        """
        Click.uz imzosini tekshirish
        """
        try:
            # Parametrlarni tartiblash
            sorted_params = sorted(params.items())
            
            # String yaratish
            param_string = ""
            for key, value in sorted_params:
                param_string += f"{key}={value}&"
            
            # Secret key qo'shish
            param_string += settings.click_secret_key
            
            # MD5 hash yaratish
            expected_signature = hashlib.md5(param_string.encode()).hexdigest()
            
            return expected_signature.lower() == received_signature.lower()
        except Exception:
            return False
    
    @staticmethod
    def sanitize_card_number(card_number: str) -> str:
        """
        Karta raqamini tozalash (faqat raqamlar)
        """
        return re.sub(r'\D', '', card_number)
    
    @staticmethod
    def mask_card_number(card_number: str) -> str:
        """
        Karta raqamini maskalash (xavfsizlik uchun)
        """
        clean_number = PaymentValidator.sanitize_card_number(card_number)
        if len(clean_number) < 6:
            return "*" * len(clean_number)
        
        # Birinchi 4 va oxirgi 4 raqamni ko'rsatish
        return f"{clean_number[:4]}{'*' * (len(clean_number) - 8)}{clean_number[-4:]}"
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """
        Telefon raqamini tekshirish (O'zbekiston formati)
        """
        # O'zbekiston telefon raqami formati: +998XXXXXXXXX
        phone_pattern = r'^\+998[0-9]{9}$'
        return bool(re.match(phone_pattern, phone))
    
    @staticmethod
    def generate_secure_token() -> str:
        """
        Xavfsiz token yaratish
        """
        import secrets
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def is_suspicious_activity(user_id: str, payment_count: int, time_window_minutes: int = 10) -> bool:
        """
        Shubhali faollikni aniqlash
        """
        # 10 daqiqa ichida 5 dan ortiq to'lov urinishi shubhali
        return payment_count > 5 and time_window_minutes <= 10