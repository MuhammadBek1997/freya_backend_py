from typing import Dict, Any, Optional

try:
    from googletrans import Translator as _GTrans
    _gtrans_available = True
except ImportError:
    _gtrans_available = False


class TranslationService:
    def __init__(self):
        self.supported_languages = {
            "uz": "Uzbek",
            "ru": "Russian",
            "en": "English",
        }

    async def _do_translate(self, text: str, dest: str, src: str = "auto") -> str:
        """Translate text using googletrans, fall back to original on failure."""
        if not _gtrans_available or not text or not text.strip():
            return text
        try:
            translator = _GTrans()
            result = await translator.translate(text, dest=dest, src=src)
            if result and result.text:
                return result.text
        except Exception:
            pass
        # Synchronous fallback via thread executor
        try:
            import asyncio
            from concurrent.futures import ThreadPoolExecutor

            def _sync_call():
                try:
                    t = _GTrans()
                    r = t.translate(text, dest=dest, src=src)
                    return r.text if r and r.text else text
                except Exception:
                    return text

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as ex:
                return await loop.run_in_executor(ex, _sync_call)
        except Exception:
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
