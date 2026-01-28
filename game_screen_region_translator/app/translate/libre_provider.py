from __future__ import annotations

import logging
import os
import time

import requests

from app.config import LibreConfig
from app.translate.base import TranslatorProvider
from app.translate.deepl_provider import _chunk_text


class LibreTranslator(TranslatorProvider):
    def __init__(self, cfg: LibreConfig, logger: logging.Logger):
        self.cfg = cfg
        self.logger = logger
        self.url = cfg.url
        self.api_key = os.getenv(cfg.api_key_env, "").strip()
        self.session = requests.Session()

    def translate(self, text: str, source_lang: str = "EN", target_lang: str = "RU", max_chars_per_chunk: int = 2500, **_) -> str:
        if not text.strip():
            return ""

        chunks = _chunk_text(text, max_chars=max_chars_per_chunk)
        out = []
        for ch in chunks:
            out.append(self._translate_one(ch, source_lang, target_lang))
        return "\n".join([p for p in out if p.strip()]).strip()

    def _translate_one(self, text: str, source_lang: str, target_lang: str) -> str:
        payload = {
            "q": text,
            "source": source_lang.lower(),
            "target": target_lang.lower(),
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key

        last_err = None
        backoff = 0.7
        for _ in range(1, 6):
            try:
                r = self.session.post(self.url, data=payload, timeout=int(self.cfg.timeout_sec))
                if r.status_code == 200:
                    return r.json().get("translatedText", "").strip()
                if r.status_code in (429, 500, 502, 503, 504):
                    last_err = RuntimeError(f"LibreTranslate: HTTP {r.status_code}")
                    time.sleep(backoff)
                    backoff *= 1.7
                    continue
                raise RuntimeError(f"LibreTranslate: HTTP {r.status_code} {r.text[:200]}")
            except requests.Timeout:
                last_err = RuntimeError("LibreTranslate: timeout")
                time.sleep(backoff)
                backoff *= 1.7
            except requests.RequestException as e:
                last_err = RuntimeError(f"LibreTranslate: network error: {e}")
                time.sleep(backoff)
                backoff *= 1.7

        raise last_err or RuntimeError("LibreTranslate: failed")
