import httpx
from typing import Dict, Any, Optional, List
from app.config import settings


class TranslationService:
    def __init__(self):
        self.api_key = settings.deepl_api_key
        self.base_url = "https://api-free.deepl.com/v2"  # Free API endpoint
        
        # Qo'llab-quvvatlanadigan tillar
        self.supported_languages = {
            "uz": "UZ",  # O'zbek tili (DeepL qo'llab-quvvatlamaydi, Google Translate ishlatish kerak)
            "ru": "RU",  # Rus tili
            "en": "EN"   # Ingliz tili
        }
        
        # DeepL qo'llab-quvvatlanadigan tillar
        self.deepl_languages = {
            "ru": "RU",
            "en": "EN-US",
            "de": "DE",
            "fr": "FR",
            "es": "ES",
            "it": "IT",
            "ja": "JA",
            "ko": "KO",
            "zh": "ZH",
            "pt": "PT",
            "pl": "PL",
            "nl": "NL",
            "sv": "SV",
            "da": "DA",
            "fi": "FI",
            "no": "NB",
            "cs": "CS",
            "sk": "SK",
            "sl": "SL",
            "et": "ET",
            "lv": "LV",
            "lt": "LT",
            "bg": "BG",
            "hu": "HU",
            "ro": "RO",
            "el": "EL",
            "tr": "TR"
        }

    async def translate_text(self, text: str, target_language: str, source_language: Optional[str] = None) -> Dict[str, Any]:
        """
        Matnni berilgan tilga tarjima qilish
        """
        try:
            if not text or text.strip() == "":
                return {
                    "success": False,
                    "error": "Tarjima qilinadigan matn bo'sh bo'lishi mumkin emas"
                }

            if not self.api_key:
                return {
                    "success": False,
                    "error": "DeepL API key sozlanmagan"
                }

            # O'zbek tili uchun maxsus ishlov (DeepL qo'llab-quvvatlamaydi)
            if target_language == "uz" or source_language == "uz":
                return await self._handle_uzbek_translation(text, target_language, source_language)

            if target_language not in self.deepl_languages:
                return {
                    "success": False,
                    "error": f"Qo'llab-quvvatlanmaydigan til: {target_language}. Mavjud tillar: {', '.join(self.deepl_languages.keys())}"
                }

            # DeepL API ga so'rov yuborish
            data = {
                "auth_key": self.api_key,
                "text": text,
                "target_lang": self.deepl_languages[target_language]
            }

            if source_language and source_language in self.deepl_languages:
                data["source_lang"] = self.deepl_languages[source_language]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/translate",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                if response.status_code == 200:
                    result = response.json()
                    translated_text = result["translations"][0]["text"]
                    detected_source_lang = result["translations"][0].get("detected_source_language", source_language)

                    return {
                        "success": True,
                        "data": {
                            "original_text": text,
                            "translated_text": translated_text,
                            "source_language": detected_source_lang or "auto-detected",
                            "target_language": target_language
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"DeepL API xatoligi: {response.status_code} - {response.text}"
                    }

        except Exception as error:
            print(f"Tarjima xatoligi: {error}")
            return {
                "success": False,
                "error": str(error)
            }

    async def _handle_uzbek_translation(self, text: str, target_language: str, source_language: Optional[str] = None) -> Dict[str, Any]:
        """
        O'zbek tili uchun maxsus ishlov (Google Translate yoki boshqa servis ishlatish kerak)
        Hozircha oddiy javob qaytaradi
        """
        return {
            "success": False,
            "error": "O'zbek tili uchun tarjima hozircha qo'llab-quvvatlanmaydi. Google Translate API kerak."
        }

    async def translate_to_all_languages(self, text: str, source_language: Optional[str] = None) -> Dict[str, Any]:
        """
        Matnni barcha qo'llab-quvvatlanadigan tillarga tarjima qilish
        """
        try:
            if not text or text.strip() == "":
                return {
                    "success": False,
                    "error": "Tarjima qilinadigan matn bo'sh bo'lishi mumkin emas"
                }

            translations = {}
            errors = []

            # Har bir til uchun tarjima qilish
            for lang_code in self.supported_languages.keys():
                if lang_code == source_language:
                    # Manba til bilan bir xil bo'lsa, o'zini qo'shish
                    translations[lang_code] = text
                    continue

                try:
                    result = await self.translate_text(text, lang_code, source_language)
                    if result["success"]:
                        translations[lang_code] = result["data"]["translated_text"]
                    else:
                        errors.append(f"{lang_code}: {result['error']}")
                except Exception as error:
                    errors.append(f"{lang_code}: {str(error)}")

            return {
                "success": len(translations) > 0,
                "data": {
                    "original_text": text,
                    "translations": translations,
                    "source_language": source_language or "auto-detected"
                },
                "errors": errors if errors else None
            }

        except Exception as error:
            print(f"Barcha tillarga tarjima xatoligi: {error}")
            return {
                "success": False,
                "error": str(error)
            }

    async def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Tilni aniqlash (DeepL bu funksiyani to'liq qo'llab-quvvatlamaydi)
        """
        try:
            if not text or text.strip() == "":
                return {
                    "success": False,
                    "error": "Tahlil qilinadigan matn bo'sh bo'lishi mumkin emas"
                }

            # Oddiy til aniqlash logikasi (haqiqiy loyihada Google Translate yoki boshqa servis ishlatish kerak)
            # Kirill harflari bo'lsa rus tili deb hisoblaymiz
            if any('\u0400' <= char <= '\u04FF' for char in text):
                return {
                    "success": True,
                    "data": {
                        "text": text,
                        "language": "ru",
                        "confidence": 0.8
                    }
                }
            # Lotin harflari bo'lsa ingliz tili deb hisoblaymiz
            elif any('a' <= char.lower() <= 'z' for char in text):
                return {
                    "success": True,
                    "data": {
                        "text": text,
                        "language": "en",
                        "confidence": 0.7
                    }
                }
            else:
                return {
                    "success": True,
                    "data": {
                        "text": text,
                        "language": "unknown",
                        "confidence": 0.1
                    }
                }

        except Exception as error:
            print(f"Til aniqlash xatoligi: {error}")
            return {
                "success": False,
                "error": str(error)
            }

    def get_supported_languages(self) -> Dict[str, Any]:
        """
        Qo'llab-quvvatlanadigan tillar ro'yxatini olish
        """
        return {
            "success": True,
            "data": self.supported_languages
        }

    async def get_usage_info(self) -> Dict[str, Any]:
        """
        DeepL API ishlatish ma'lumotlarini olish
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "DeepL API key sozlanmagan"
                }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/usage",
                    data={"auth_key": self.api_key},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                if response.status_code == 200:
                    usage_data = response.json()
                    return {
                        "success": True,
                        "data": usage_data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"DeepL API xatoligi: {response.status_code} - {response.text}"
                    }

        except Exception as error:
            print(f"Usage info xatoligi: {error}")
            return {
                "success": False,
                "error": str(error)
            }


# Singleton instance
translation_service = TranslationService()