from typing import Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    from googletrans import Translator as _GTrans
    _gtrans_available = True
except ImportError:
    _gtrans_available = False


def _http_translate(text: str, dest: str, src: str = "auto") -> str:
    """Translate via direct HTTP request to Google Translate free API."""
    try:
        import requests as _req
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": src, "tl": dest, "dt": "t", "q": text}
        resp = _req.get(url, params=params, timeout=8)
        data = resp.json()
        parts = [seg[0] for seg in data[0] if seg and seg[0]]
        translated = "".join(parts)
        return translated if translated.strip() else text
    except Exception:
        return text


class TranslationService:
    def __init__(self):
        self.supported_languages = {
            "uz": "Uzbek",
            "ru": "Russian",
            "en": "English",
        }

    async def _do_translate(self, text: str, dest: str, src: str = "auto") -> str:
        """Translate text: direct HTTP → googletrans → original text fallback."""
        if not text or not text.strip():
            return text
        try:
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=1) as ex:
                result = await loop.run_in_executor(ex, _http_translate, text, dest, src)
            if result and result.strip() and result != text:
                return result
        except Exception:
            pass
        # googletrans fallback
        if _gtrans_available:
            try:
                translator = _GTrans()
                r = await translator.translate(text, dest=dest, src=src)
                if r and r.text and r.text.strip():
                    return r.text
            except Exception:
                pass
        return text

    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            if not text or text.strip() == "":
                return {"success": False, "error": "Empty text"}

            translated = await self._do_translate(
                text, target_language, source_language or "auto"
            )
            return {
                "success": True,
                "data": {
                    "original_text": text,
                    "translated_text": translated,
                    "source_language": source_language or "auto",
                    "target_language": target_language,
                },
            }
        except Exception as error:
            return {"success": False, "error": str(error)}

    async def translate_to_all_languages(
        self, text: str, source_language: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            if not text or text.strip() == "":
                return {"success": False, "error": "Empty text"}

            translations: Dict[str, str] = {}
            for lang_code in self.supported_languages:
                if lang_code == source_language:
                    translations[lang_code] = text
                else:
                    translations[lang_code] = await self._do_translate(
                        text, lang_code, source_language or "auto"
                    )

            return {
                "success": True,
                "data": {
                    "original_text": text,
                    "translations": translations,
                    "source_language": source_language or "auto",
                },
                "errors": None,
            }
        except Exception as error:
            return {"success": False, "error": str(error)}

    async def detect_language(self, text: str) -> Dict[str, Any]:
        try:
            if not text or text.strip() == "":
                return {"success": False, "error": "Empty text"}

            if _gtrans_available:
                try:
                    translator = _GTrans()
                    detected = await translator.detect(text)
                    lang = detected.lang if detected and detected.lang else "uz"
                    return {
                        "success": True,
                        "data": {"text": text, "language": lang, "confidence": 1.0},
                    }
                except Exception:
                    pass

            return {
                "success": True,
                "data": {"text": text, "language": "uz", "confidence": 1.0},
            }
        except Exception as error:
            return {
                "success": False,
                "error": str(error),
                "data": {"language": "uz"},
            }

    def get_supported_languages(self) -> Dict[str, Any]:
        return {"success": True, "data": self.supported_languages}

    async def get_usage_info(self) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {"provider": "googletrans", "free": True, "available": _gtrans_available},
        }


# Singleton instance
translation_service = TranslationService()
