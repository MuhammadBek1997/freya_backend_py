from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional
from app.services.translation_service import translation_service
from app.middleware.auth import get_current_admin
from app.models import Admin
from pydantic import BaseModel


class TranslateTextRequest(BaseModel):
    text: str
    target_language: str
    source_language: Optional[str] = None


class TranslateToAllLanguagesRequest(BaseModel):
    text: str
    source_language: Optional[str] = None


class DetectLanguageRequest(BaseModel):
    text: str


router = APIRouter(prefix="/translation", tags=["Translation"])


@router.post("/translate", summary="Matnni tarjima qilish (Google Translate)")
async def translate_text(
    request: TranslateTextRequest,
    current_admin: Admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Matnni berilgan tilga tarjima qilish (googletrans)
    
    - **text**: Tarjima qilinadigan matn
    - **target_language**: Maqsadli til kodi (uz, ru, en)
    - **source_language**: Manba til kodi (ixtiyoriy)
    """
    try:
        result = await translation_service.translate_text(
            text=request.text,
            target_language=request.target_language,
            source_language=request.source_language
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": "Matn muvaffaqiyatli tarjima qilindi",
            "data": result["data"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tarjima qilishda xatolik: {str(e)}"
        )


@router.post("/translate-all", summary="Matnni barcha tillarga tarjima qilish (Google Translate)")
async def translate_to_all_languages(
    request: TranslateToAllLanguagesRequest,
    current_admin: Admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Matnni qo'llab-quvvatlanadigan tillarga googletrans yordamida tarjima qilish
    
    - **text**: Tarjima qilinadigan matn
    - **source_language**: Manba til kodi (ixtiyoriy)
    """
    try:
        result = await translation_service.translate_to_all_languages(
            text=request.text,
            source_language=request.source_language
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": "Matn barcha tillarga muvaffaqiyatli tarjima qilindi",
            "data": result["data"],
            "errors": result.get("errors")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tarjima qilishda xatolik: {str(e)}"
        )


@router.post("/detect-language", summary="Matn tilini aniqlash (Google Translate)")
async def detect_language(
    request: DetectLanguageRequest,
    current_admin: Admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Matn tilini googletrans orqali aniqlash
    
    - **text**: Tahlil qilinadigan matn
    """
    try:
        result = await translation_service.detect_language(request.text)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": "Til muvaffaqiyatli aniqlandi",
            "data": result["data"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tilni aniqlashda xatolik: {str(e)}"
        )


@router.get("/supported-languages", summary="Qo'llab-quvvatlanadigan tillar (Google Translate)")
async def get_supported_languages() -> Dict[str, Any]:
    """
    Qo'llab-quvvatlanadigan tillar ro'yxatini olish
    """
    try:
        result = translation_service.get_supported_languages()
        
        return {
            "success": True,
            "message": "Qo'llab-quvvatlanadigan tillar ro'yxati",
            "data": result["data"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tillar ro'yxatini olishda xatolik: {str(e)}"
        )


# @router.get("/usage", summary="Google Translate usage (qo'llab-quvvatlanmaydi)")
# async def get_usage_info(
#     current_admin: Admin = Depends(get_current_admin)
# ) -> Dict[str, Any]:
#     """
#     Google Translate uchun usage statistikasi mavjud emas
#     """
#     try:
#         result = await translation_service.get_usage_info()
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=result["error"]
#             )
        
#         return {
#             "success": True,
#             "message": "API ishlatish ma'lumotlari",
#             "data": result["data"]
#         }
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"API ma'lumotlarini olishda xatolik: {str(e)}"
#         )