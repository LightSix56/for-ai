from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "logs/app.log"


@dataclass
class HotkeyConfig:
    toggle: str = "CTRL+SHIFT+T"
    close: str = "CTRL+SHIFT+ESC"


@dataclass
class OverlayConfig:
    click_through: bool = True
    background_dimming: float = 0.55
    padding_px: int = 10
    base_font_size: int = 22
    min_font_size: int = 12
    max_width_px: int = 1600
    max_height_px: int = 900


@dataclass
class CaptureConfig:
    backend_order: list = None
    black_threshold_mean: float = 8.0
    black_threshold_nonzero_ratio: float = 0.02


@dataclass
class OcrConfig:
    lang: str = "eng"
    psm: int = 6
    oem: int = 1
    scale_factor: int = 3
    threshold_mode: str = "otsu"
    try_shadow_removal: bool = True
    whitelist: str = ""
    min_text_length: int = 3
    tessdata_dir: str = ""


@dataclass
class DeeplConfig:
    auth_key_env: str = "DEEPL_AUTH_KEY"
    use_free_api: bool = True
    timeout_sec: int = 10


@dataclass
class LibreConfig:
    url: str = "https://libretranslate.com/translate"
    api_key_env: str = "LIBRETRANSLATE_API_KEY"
    timeout_sec: int = 12


@dataclass
class TranslationConfig:
    provider: str = "deepl"
    cache_ttl_sec: int = 90
    max_chars_per_chunk: int = 2500
    deepl: DeeplConfig = None
    libre: LibreConfig = None
    
    def __post_init__(self):
        if self.deepl is None:
            self.deepl = DeeplConfig()
        if self.libre is None:
            self.libre = LibreConfig()


@dataclass
class AppConfig:
    logging: LoggingConfig = None
    hotkeys: HotkeyConfig = None
    overlay: OverlayConfig = None
    capture: CaptureConfig = None
    ocr: OcrConfig = None
    translation: TranslationConfig = None
    
    def __post_init__(self):
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.hotkeys is None:
            self.hotkeys = HotkeyConfig()
        if self.overlay is None:
            self.overlay = OverlayConfig()
        if self.capture is None:
            self.capture = CaptureConfig(backend_order=["mss", "dxcam"])
        if self.ocr is None:
            self.ocr = OcrConfig()
        if self.translation is None:
            self.translation = TranslationConfig()

    @staticmethod
    def _merge(dst: dict, src: dict) -> dict:
        for k, v in src.items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                dst[k] = AppConfig._merge(dst[k], v)
            else:
                dst[k] = v
        return dst

    @classmethod
    def load(cls, path: str) -> "AppConfig":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        cfg = cls()

        if "logging" in raw:
            cfg.logging = LoggingConfig(**raw["logging"])
        if "hotkeys" in raw:
            cfg.hotkeys = HotkeyConfig(**raw["hotkeys"])
        if "overlay" in raw:
            cfg.overlay = OverlayConfig(**raw["overlay"])
        if "capture" in raw:
            cap = dict(raw["capture"])
            if "backend_order" not in cap or cap["backend_order"] is None:
                cap["backend_order"] = ["mss", "dxcam"]
            cfg.capture = CaptureConfig(**cap)
        if "ocr" in raw:
            cfg.ocr = OcrConfig(**raw["ocr"])
        if "translation" in raw:
            tr = dict(raw["translation"])
            deepl = tr.get("deepl", {})
            libre = tr.get("libre", {})
            cfg.translation = TranslationConfig(
                provider=tr.get("provider", "deepl"),
                cache_ttl_sec=tr.get("cache_ttl_sec", 90),
                max_chars_per_chunk=tr.get("max_chars_per_chunk", 2500),
                deepl=DeeplConfig(**deepl) if isinstance(deepl, dict) else DeeplConfig(),
                libre=LibreConfig(**libre) if isinstance(libre, dict) else LibreConfig(),
            )

        return cfg

    def save(self, path: str) -> None:
        raw = {
            "logging": self.logging.__dict__,
            "hotkeys": self.hotkeys.__dict__,
            "overlay": self.overlay.__dict__,
            "capture": {"backend_order": self.capture.backend_order, "black_threshold_mean": self.capture.black_threshold_mean, "black_threshold_nonzero_ratio": self.capture.black_threshold_nonzero_ratio},
            "ocr": self.ocr.__dict__,
            "translation": {
                "provider": self.translation.provider,
                "cache_ttl_sec": self.translation.cache_ttl_sec,
                "max_chars_per_chunk": self.translation.max_chars_per_chunk,
                "deepl": self.translation.deepl.__dict__,
                "libre": self.translation.libre.__dict__,
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
