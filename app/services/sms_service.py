import httpx
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config import settings
import random

logger = logging.getLogger(__name__)

class SMSService:
    """
    Eskiz.uz SMS service for sending SMS messages
    """
    
    def __init__(self):
        self.token = settings.eskiz_token
        self.base_url = "https://notify.eskiz.uz/api"
        self.token_expiry = None
        self.refresh_in_progress = False
        
    async def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Send SMS via Eskiz.uz
        
        Args:
            phone: Phone number in format +998901234567
            message: SMS text
            
        Returns:
            Dict with success status and data/error
        """
        try:
            # Ensure valid token
            await self.ensure_valid_token()
            
            if not self.token:
                return {
                    "success": False,
                    "error": "Token olishda xatolik"
                }
            
            # Format phone number (only digits)
            formatted_phone = ''.join(filter(str.isdigit, phone))
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/message/sms/send",
                    json={
                        "mobile_phone": formatted_phone,
                        "message": message,
                        "from": "4546",
                        "callback_url": None
                    },
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "data": data,
                        "message_id": data.get("id")
                    }
                else:
                    # Handle token expiry
                    if response.status_code in [401, 403]:
                        logger.info("Token muddati tugagan, yangilanmoqda...")
                        self.token = None
                        self.token_expiry = None
                        
                        refresh_result = await self.refresh_token()
                        if refresh_result["success"]:
                            logger.info("Token yangilandi, qayta urinish...")
                            return await self.send_sms(phone, message)
                    
                    return {
                        "success": False,
                        "error": response.json().get("message", "SMS yuborishda xatolik")
                    }
                    
        except Exception as e:
            logger.error(f"SMS yuborishda xatolik: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_verification_code(self) -> str:
        """Generate random 6-digit verification code"""
        return str(random.randint(100000, 999999))
    
    async def send_verification_code(self, phone: str, code: Optional[str] = None) -> Dict[str, Any]:
        """
        Send verification code for registration
        
        Args:
            phone: Phone number
            code: Verification code (optional, will generate random if not provided)
            
        Returns:
            Dict with success status, data/error and verification code
        """
        verification_code = code or self.generate_verification_code()
        
        # Eskiz.uz approved template #2
        message = f"Freya mobil ilovasiga ro'yxatdan o'tish uchun tasdiqlash kodi: {verification_code}"
        
        result = await self.send_sms(phone, message)
        
        if result["success"]:
            result["verification_code"] = verification_code
            
        return result
    
    async def send_password_reset_code(self, phone: str, code: Optional[str] = None) -> Dict[str, Any]:
        """Send password reset verification code"""
        verification_code = code or self.generate_verification_code()
        
        message = f"Freya ilovasida parolni tiklash uchun tasdiqlash kodi: {verification_code}"
        
        result = await self.send_sms(phone, message)
        
        if result["success"]:
            result["verification_code"] = verification_code
            
        return result
    
    async def send_phone_change_code(self, phone: str, code: Optional[str] = None) -> Dict[str, Any]:
        """Send phone number change verification code"""
        verification_code = code or self.generate_verification_code()
        
        message = f"Freya ilovasida telefon raqamini o'zgartirish uchun tasdiqlash kodi: {verification_code}"
        
        result = await self.send_sms(phone, message)
        
        if result["success"]:
            result["verification_code"] = verification_code
            
        return result
    
    async def send_registration_code(self, phone: str, code: Optional[str] = None) -> Dict[str, Any]:
        """Send registration verification code"""
        verification_code = code or self.generate_verification_code()
        
        message = f"Freya ilovasiga ro'yxatdan o'tish uchun tasdiqlash kodi: {verification_code}. Kodni hech kimga bermang!"
        
        result = await self.send_sms(phone, message)
        
        if result["success"]:
            result["verification_code"] = verification_code
            
        return result
    
    async def send_payment_card_verification_code(self, phone: str, card_number: str, code: Optional[str] = None) -> Dict[str, Any]:
        """Send payment card verification code"""
        verification_code = code or self.generate_verification_code()
        
        # Mask card number for security
        masked_card = f"****{card_number[-4:]}" if len(card_number) >= 4 else card_number
        
        message = f"Freya ilovasida {masked_card} kartani tasdiqlash uchun kod: {verification_code}"
        
        result = await self.send_sms(phone, message)
        
        if result["success"]:
            result["verification_code"] = verification_code
            
        return result
    
    async def ensure_valid_token(self):
        """Ensure we have a valid token"""
        if not self.token or (self.token_expiry and datetime.now() >= self.token_expiry):
            if not self.refresh_in_progress:
                await self.refresh_token()
    
    async def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh Eskiz.uz authentication token
        
        Returns:
            Dict with success status and data/error
        """
        if self.refresh_in_progress:
            # Wait for ongoing refresh
            while self.refresh_in_progress:
                await asyncio.sleep(0.1)
            return {"success": bool(self.token)}
        
        self.refresh_in_progress = True
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/auth/login",
                    json={
                        "email": settings.eskiz_email,
                        "password": settings.eskiz_password
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("message") == "token_generated":
                        self.token = data["data"]["token"]
                        # Set token expiry (usually 30 days, but we'll refresh every 25 days to be safe)
                        self.token_expiry = datetime.now() + timedelta(days=25)
                        
                        logger.info("Eskiz.uz token muvaffaqiyatli yangilandi")
                        
                        return {
                            "success": True,
                            "token": self.token,
                            "expires_at": self.token_expiry
                        }
                    else:
                        logger.error(f"Token yaratishda xatolik: {data}")
                        return {
                            "success": False,
                            "error": data.get("message", "Token yaratishda xatolik")
                        }
                else:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"message": "Unknown error"}
                    logger.error(f"Eskiz.uz autentifikatsiya xatoligi: {error_data}")
                    return {
                        "success": False,
                        "error": error_data.get("message", "Autentifikatsiya xatoligi")
                    }
                    
        except Exception as e:
            logger.error(f"Token yangilashda xatolik: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            self.refresh_in_progress = False
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        Get SMS balance from Eskiz.uz
        
        Returns:
            Dict with success status and balance data
        """
        try:
            await self.ensure_valid_token()
            
            if not self.token:
                return {
                    "success": False,
                    "error": "Token mavjud emas"
                }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/user/get-limit",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "balance": data["data"]
                    }
                else:
                    return {
                        "success": False,
                        "error": "Balansni olishda xatolik"
                    }
                    
        except Exception as e:
            logger.error(f"Balansni olishda xatolik: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_sms_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get SMS delivery status
        
        Args:
            message_id: SMS message ID
            
        Returns:
            Dict with success status and delivery status
        """
        try:
            await self.ensure_valid_token()
            
            if not self.token:
                return {
                    "success": False,
                    "error": "Token mavjud emas"
                }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/message/sms/status/{message_id}",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "status": data["data"]
                    }
                else:
                    return {
                        "success": False,
                        "error": "SMS statusini olishda xatolik"
                    }
                    
        except Exception as e:
            logger.error(f"SMS statusini olishda xatolik: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# Global SMS service instance
sms_service = SMSService()