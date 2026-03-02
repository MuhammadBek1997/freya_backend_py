from typing import Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    from googletrans import Translator as _GTrans
    _gtrans_available = True
except ImportError:
    _gtrans_available = False

try:
    from deep_translator import GoogleTranslator as _DeepGT, MyMemoryTranslator as _DeepMM
    _deep_translator_available = True
except ImportError:
    _deep_translator_available = False


def _sync_translate(text: str, dest: str, src: str = "auto") -> str:
    """Sync translation: deep_translator → direct HTTP → MyMemory → source text."""
    src_lang = src if src != "auto" else "auto"

    # 1) deep_translator GoogleTranslator (most reliable)
    if _deep_translator_available:
        try:
            result = _DeepGT(source=src_lang, target=dest).translate(text)
            if result and result.strip() and result.strip().lower() != text.strip().lower():
                return result
        except Exception:
            pass

        # 2) deep_translator MyMemoryTranslator
        try:
            result = _DeepMM(source=src_lang, target=dest).translate(text)
            if result and result.strip() and result.strip().lower() != text.strip().lower():
                return result
        except Exception:
            pass

    # 3) Direct HTTP to Google Translate
    try:
        import requests as _req
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": src, "tl": dest, "dt": "t", "q": text}
        resp = _req.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        parts = [seg[0] for seg in data[0] if seg and seg[0]]
        translated = "".join(parts)
        if translated.strip() and translated.strip().lower() != text.strip().lower():
            return translated
    except Exception:
        pass

    # 4) MyMemory direct HTTP
    try:
        import requests as _req
        lang_pair = f"{src}|{dest}" if src != "auto" else f"uz|{dest}"
        resp2 = _req.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": lang_pair},
            timeout=10,
        )
        t2 = resp2.json().get("responseData", {}).get("translatedText", "")
        if t2 and t2.strip() and t2.strip().lower() != text.strip().lower():
            return t2
    except Exception:
        pass

    return text


class TranslationService:
    def __init__(self):
        self.supported_languages = {
            "uz": "Uzbek",
            "ru": "Russian",
            "en": "English",
        }

    async def _do_translate(self, text: str, dest: str, src: str = "auto") -> str:
        """Translate text using all available methods, fall back to source text."""
        if not text or not text.strip():
            return text
        try:
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=1) as ex:
                result = await loop.run_in_executor(ex, _sync_translate, text, dest, src)
            if result and result.strip() and result != text:
                return result
        except Exception:
            pass
        # googletrans async fallback
        if _gtrans_available:
            try:
                r = await _GTrans().translate(text, dest=dest, src=src)
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
