from __future__ import annotations

import hashlib
import logging

from cachetools import TTLCache

from app.translate.base import TranslatorProvider


class CachedTranslator(TranslatorProvider):
    def __init__(self, base: TranslatorProvider, ttl_sec: int, logger: logging.Logger):
        self.base = base
        self.logger = logger
        self.cache = TTLCache(maxsize=256, ttl=int(ttl_sec))

    def translate(self, text: str, source_lang: str = "EN", target_lang: str = "RU", **kwargs) -> str:
        key = self._key(text, source_lang, target_lang)
        if key in self.cache:
            self.logger.info("Translate cache hit")
            return self.cache[key]
        out = self.base.translate(text, source_lang=source_lang, target_lang=target_lang, **kwargs)
        self.cache[key] = out
        return out

    def _key(self, text: str, source_lang: str, target_lang: str) -> str:
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{source_lang}->{target_lang}:{h}"
