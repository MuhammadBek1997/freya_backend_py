# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from typing import Dict, Any
# from app.database import get_db
# from app.services.sms_service import sms_service
# from app.middleware.auth import get_current_admin
# from app.models import Admin
# from pydantic import BaseModel


# class SendVerificationCodeRequest(BaseModel):
#     phone: str


# class SendResetPasswordCodeRequest(BaseModel):
#     phone: str


# class SendChangePhoneCodeRequest(BaseModel):
#     old_phone: str
#     new_phone: str


# class SendRegistrationCodeRequest(BaseModel):
#     phone: str


# class SendPaymentCardCodeRequest(BaseModel):
#     phone: str
#     card_number: str


# class CheckBalanceRequest(BaseModel):
#     pass


# class CheckSMSStatusRequest(BaseModel):
#     message_id: str


# router = APIRouter(prefix="/sms", tags=["SMS"])


# @router.post("/send-verification-code", summary="Tasdiqlash kodini yuborish")
# async def send_verification_code(
#     request: SendVerificationCodeRequest,
#     current_admin: Admin = Depends(get_current_admin),
#     db: Session = Depends(get_db)
# ) -> Dict[str, Any]:
#     """
#     Telefon raqamini tasdiqlash uchun kod yuborish
    
#     - **phone**: Telefon raqami (+998901234567 formatida)
#     """
#     try:
#         result = await sms_service.send_verification_code(request.phone)
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=result["error"]
#             )
        
#         return {
#             "success": True,
#             "message": "Tasdiqlash kodi muvaffaqiyatli yuborildi",
#             "data": result
#         }
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"SMS yuborishda xatolik: {str(e)}"
#         )


# @router.post("/send-reset-password-code", summary="Parolni tiklash kodini yuborish")
# async def send_reset_password_code(
#     request: SendResetPasswordCodeRequest
# ) -> Dict[str, Any]:
#     """
#     Parolni tiklash uchun kod yuborish
    
#     - **phone**: Telefon raqami (+998901234567 formatida)
#     """
#     try:
#         result = await sms_service.send_reset_password_code(request.phone)
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=result["error"]
#             )
        
#         return {
#             "success": True,
#             "message": "Parolni tiklash kodi muvaffaqiyatli yuborildi",
#             "data": result
#         }
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"SMS yuborishda xatolik: {str(e)}"
#         )


# @router.post("/send-change-phone-code", summary="Telefon raqamini o'zgartirish kodini yuborish")
# async def send_change_phone_code(
#     request: SendChangePhoneCodeRequest,
#     current_admin: Admin = Depends(get_current_admin)
# ) -> Dict[str, Any]:
#     """
#     Telefon raqamini o'zgartirish uchun kod yuborish
    
#     - **old_phone**: Eski telefon raqami
#     - **new_phone**: Yangi telefon raqami
#     """
#     try:
#         result = await sms_service.send_change_phone_code(request.old_phone, request.new_phone)
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=result["error"]
#             )
        
#         return {
#             "success": True,
#             "message": "Telefon o'zgartirish kodi muvaffaqiyatli yuborildi",
#             "data": result
#         }
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"SMS yuborishda xatolik: {str(e)}"
#         )


# @router.post("/send-registration-code", summary="Ro'yxatdan o'tish kodini yuborish")
# async def send_registration_code(
#     request: SendRegistrationCodeRequest
# ) -> Dict[str, Any]:
#     """
#     Ro'yxatdan o'tish uchun kod yuborish
    
#     - **phone**: Telefon raqami (+998901234567 formatida)
#     """
#     try:
#         result = await sms_service.send_registration_code(request.phone)
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=result["error"]
#             )
        
#         return {
#             "success": True,
#             "message": "Ro'yxatdan o'tish kodi muvaffaqiyatli yuborildi",
#             "data": result
#         }
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"SMS yuborishda xatolik: {str(e)}"
#         )


# @router.post("/send-payment-card-code", summary="To'lov kartasi tasdiqlash kodini yuborish")
# async def send_payment_card_code(
#     request: SendPaymentCardCodeRequest,
#     current_admin: Admin = Depends(get_current_admin)
# ) -> Dict[str, Any]:
#     """
#     To'lov kartasini tasdiqlash uchun kod yuborish
    
#     - **phone**: Telefon raqami
#     - **card_number**: Karta raqami
#     """
#     try:
#         result = await sms_service.send_payment_card_code(request.phone, request.card_number)
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=result["error"]
#             )
        
#         return {
#             "success": True,
#             "message": "To'lov kartasi tasdiqlash kodi muvaffaqiyatli yuborildi",
#             "data": result
#         }
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"SMS yuborishda xatolik: {str(e)}"
#         )


# @router.get("/balance", summary="SMS balansini tekshirish")
# async def check_sms_balance(
#     current_admin: Admin = Depends(get_current_admin)
# ) -> Dict[str, Any]:
#     """
#     Eskiz.uz hisobidagi SMS balansini tekshirish
#     """
#     try:
#         result = await sms_service.get_balance()
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=result["error"]
#             )
        
#         return {
#             "success": True,
#             "message": "Balans muvaffaqiyatli olindi",
#             "data": result
#         }
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Balansni tekshirishda xatolik: {str(e)}"
#         )


# @router.get("/status/{message_id}", summary="SMS holatini tekshirish")
# async def check_sms_status(
#     message_id: str,
#     current_admin: Admin = Depends(get_current_admin)
# ) -> Dict[str, Any]:
#     """
#     Yuborilgan SMS holatini tekshirish
    
#     - **message_id**: SMS ID
#     """
#     try:
#         result = await sms_service.check_sms_status(message_id)
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=result["error"]
#             )
        
#         return {
#             "success": True,
#             "message": "SMS holati muvaffaqiyatli olindi",
#             "data": result
#         }
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"SMS holatini tekshirishda xatolik: {str(e)}"
#         )


# @router.post("/refresh-token", summary="Eskiz.uz tokenini yangilash")
# async def refresh_eskiz_token(
#     current_admin: Admin = Depends(get_current_admin)
# ) -> Dict[str, Any]:
#     """
#     Eskiz.uz access tokenini yangilash
#     """
#     try:
#         result = await sms_service.refresh_token()
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=result["error"]
#             )
        
#         return {
#             "success": True,
#             "message": "Token muvaffaqiyatli yangilandi",
#             "data": result
#         }
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Tokenni yangilashda xatolik: {str(e)}"
#         )