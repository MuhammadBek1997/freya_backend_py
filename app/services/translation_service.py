from typing import Dict, Any, Optional
from googletrans import Translator


class TranslationService:
    def __init__(self):
        # Google Translate client
        self.translator = Translator()
        # Qo'llab-quvvatlanadigan tillar (kodeklar)
        self.supported_languages = {
            "uz": "Uzbek",
            "ru": "Russian",
            "en": "English",
        }

    async def translate_text(self, text: str, target_language: str, source_language: Optional[str] = None) -> Dict[str, Any]:
        """Matnni Google Translate yordamida tarjima qilish"""
        try:
            if not text or text.strip() == "":
                return {"success": False, "error": "Tarjima qilinadigan matn bo'sh bo'lishi mumkin emas"}

            # Google Translate (googletrans) ga murojaat
            res = self.translator.translate(text, dest=target_language, src=source_language or "auto")

            return {
                "success": True,
                "data": {
                    "original_text": text,
                    "translated_text": res.text,
                    "source_language": res.src or source_language or "auto",
                    "target_language": target_language,
                },
            }
        except Exception as error:
            return {"success": False, "error": str(error)}

    async def _handle_uzbek_translation(self, *args, **kwargs) -> Dict[str, Any]:
        # Legacy placeholder – endi googletrans uz tilini qo'llab-quvvatlaydi
        return {"success": True, "data": {}}

    async def translate_to_all_languages(self, text: str, source_language: Optional[str] = None) -> Dict[str, Any]:
        """Matnni qo'llab-quvvatlanadigan tillarga googletrans bilan tarjima qilish"""
        try:
            if not text or text.strip() == "":
                return {"success": False, "error": "Tarjima qilinadigan matn bo'sh bo'lishi mumkin emas"}

            translations: Dict[str, str] = {}
            errors = []

            for lang_code in self.supported_languages.keys():
                if source_language and lang_code == source_language:
                    translations[lang_code] = text
                    continue
                try:
                    res = self.translator.translate(text, dest=lang_code, src=source_language or "auto")
                    translations[lang_code] = res.text
                except Exception as error:
                    errors.append(f"{lang_code}: {str(error)}")

            return {
                "success": True,
                "data": {
                    "original_text": text,
                    "translations": translations,
                    "source_language": source_language or "auto",
                },
                "errors": errors or None,
            }
        except Exception as error:
            return {"success": False, "error": str(error)}

    async def detect_language(self, text: str) -> Dict[str, Any]:
        """Matn tilini googletrans yordamida aniqlash"""
        try:
            if not text or text.strip() == "":
                return {"success": False, "error": "Tahlil qilinadigan matn bo'sh bo'lishi mumkin emas"}
            res = self.translator.detect(text)
            return {
                "success": True,
                "data": {
                    "text": text,
                    "language": res.lang,
                    "confidence": res.confidence,
                },
            }
        except Exception as error:
            return {"success": False, "error": str(error)}

    def get_supported_languages(self) -> Dict[str, Any]:
        """Qo'llab-quvvatlanadigan tillar ro'yxati"""
        return {"success": True, "data": self.supported_languages}

    async def get_usage_info(self) -> Dict[str, Any]:
        """Google Translate uchun usage statistikasi mavjud emas"""
        return {"success": False, "error": "Usage statistikasi qo'llab-quvvatlanmaydi (googletrans)"}


# Singleton instance
translation_service = TranslationService()