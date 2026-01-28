from __future__ import annotations

import logging
import os
import re
import time
from typing import List

import requests

from app.config import DeeplConfig
from app.translate.base import TranslatorProvider


class DeepLTranslator(TranslatorProvider):
    def __init__(self, cfg: DeeplConfig, logger: logging.Logger):
        self.cfg = cfg
        self.logger = logger

        self.auth_key = os.getenv(cfg.auth_key_env, "").strip()
        if not self.auth_key:
            self.logger.warning(f"DeepL key env {cfg.auth_key_env} is empty")

        self.endpoint = "https://api-free.deepl.com/v2/translate" if cfg.use_free_api else "https://api.deepl.com/v2/translate"
        self.session = requests.Session()

    def translate(self, text: str, source_lang: str = "EN", target_lang: str = "RU", max_chars_per_chunk: int = 2500, **_) -> str:
        if not text.strip():
            return ""
        if not self.auth_key:
            raise RuntimeError("DeepL: empty API key (check .env / DEEPL_AUTH_KEY)")

        chunks = _chunk_text(text, max_chars=max_chars_per_chunk)
        out_parts = []
        for ch in chunks:
            out_parts.append(self._translate_one(ch, source_lang, target_lang))
        return "\n".join([p for p in out_parts if p.strip()]).strip()

    def _translate_one(self, text: str, source_lang: str, target_lang: str) -> str:
        payload = {
            "auth_key": self.auth_key,
            "text": text,
            "source_lang": source_lang.upper(),
            "target_lang": target_lang.upper(),
        }

        last_err = None
        backoff = 0.7
        for attempt in range(1, 6):
            try:
                r = self.session.post(self.endpoint, data=payload, timeout=int(self.cfg.timeout_sec))
                if r.status_code == 200:
                    data = r.json()
                    tr = data["translations"][0]["text"]
                    return tr
                if r.status_code in (401, 403):
                    raise RuntimeError("DeepL: invalid API key / forbidden")
                if r.status_code in (429, 500, 502, 503, 504):
                    last_err = RuntimeError(f"DeepL: HTTP {r.status_code}")
                    time.sleep(backoff)
                    backoff *= 1.7
                    continue
                raise RuntimeError(f"DeepL: HTTP {r.status_code} {r.text[:200]}")
            except requests.Timeout:
                last_err = RuntimeError("DeepL: timeout")
                time.sleep(backoff)
                backoff *= 1.7
            except requests.RequestException as e:
                last_err = RuntimeError(f"DeepL: network error: {e}")
                time.sleep(backoff)
                backoff *= 1.7

        raise last_err or RuntimeError("DeepL: failed")


def _chunk_text(text: str, max_chars: int) -> List[str]:
    text = text.replace("\r", "").strip()
    if len(text) <= max_chars:
        return [text]

    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []

    for p in paras:
        if len(p) <= max_chars:
            chunks.append(p)
            continue

        sents = re.split(r"(?<=[.!?])\s+", p)
        cur = ""
        for s in sents:
            if not s:
                continue
            if len(cur) + len(s) + 1 <= max_chars:
                cur = (cur + " " + s).strip()
            else:
                if cur:
                    chunks.append(cur)
                cur = s.strip()
        if cur:
            chunks.append(cur)

    final = []
    for c in chunks:
        if len(c) <= max_chars:
            final.append(c)
        else:
            for i in range(0, len(c), max_chars):
                final.append(c[i:i + max_chars])
    return final
