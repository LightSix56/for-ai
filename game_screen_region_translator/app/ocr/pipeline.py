from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image
import pytesseract

from app.config import OcrConfig


@dataclass
class OcrResult:
    text: str
    best_pass: str
    best_conf: float
    debug: dict


class OcrPipeline:
    def __init__(self, cfg: OcrConfig, logger: logging.Logger):
        self.cfg = cfg
        self.logger = logger

    def run(self, img: Image.Image) -> OcrResult:
        passes = [
            ("A_upscale_otsu", self._pass_a),
            ("B_maxchannel", self._pass_b),
            ("C_shadow_removal", self._pass_c if self.cfg.try_shadow_removal else None),
            ("D_adaptive", self._pass_d),
        ]

        best_text = ""
        best_conf = -1.0
        best_name = "none"
        debug = {}

        for name, fn in passes:
            if fn is None:
                continue
            try:
                pre = fn(img)
                text, conf = self._tesseract(pre)
                debug[name] = {"conf": conf, "len": len(text)}
                self.logger.info(f"OCR pass={name} conf={conf:.1f} len={len(text)}")
                if self._is_better(text, conf, best_text, best_conf):
                    best_text, best_conf, best_name = text, conf, name
            except Exception as e:
                debug[name] = {"error": str(e)}
                self.logger.warning(f"OCR pass={name} failed: {e}")

        best_text = self._cleanup(best_text)
        if len(best_text) < int(self.cfg.min_text_length):
            return OcrResult(text="", best_pass=best_name, best_conf=best_conf, debug=debug)

        return OcrResult(text=best_text, best_pass=best_name, best_conf=best_conf, debug=debug)

    def _is_better(self, text: str, conf: float, best_text: str, best_conf: float) -> bool:
        text = (text or "").strip()
        best_text = (best_text or "").strip()
        if not text:
            return False
        if conf > best_conf + 2.0:
            return True
        if abs(conf - best_conf) <= 2.0 and len(text) > len(best_text) + 3:
            return True
        return False

    def _cleanup(self, text: str) -> str:
        text = (text or "").replace("\r", "")
        lines = [ln.strip() for ln in text.split("\n")]
        lines = [ln for ln in lines if ln]
        return "\n".join(lines)

    def _to_np_rgb(self, img: Image.Image) -> np.ndarray:
        return np.asarray(img.convert("RGB"), dtype=np.uint8)

    def _upscale_nn(self, img: np.ndarray, scale: int) -> np.ndarray:
        h, w = img.shape[:2]
        return cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_NEAREST)

    def _threshold(self, gray: np.ndarray) -> np.ndarray:
        if self.cfg.threshold_mode == "adaptive":
            return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 8)
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return th

    def _pass_a(self, img: Image.Image) -> Image.Image:
        arr = self._to_np_rgb(img)
        arr = self._upscale_nn(arr, int(self.cfg.scale_factor))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        th = self._threshold(gray)
        th = cv2.medianBlur(th, 3)
        return Image.fromarray(th, mode="L")

    def _pass_b(self, img: Image.Image) -> Image.Image:
        arr = self._to_np_rgb(img)
        arr = self._upscale_nn(arr, int(self.cfg.scale_factor))
        mx = arr.max(axis=2).astype(np.uint8)
        th = self._threshold(mx)
        th = cv2.medianBlur(th, 3)
        return Image.fromarray(th, mode="L")

    def _pass_c(self, img: Image.Image) -> Image.Image:
        arr = self._to_np_rgb(img)
        arr = self._upscale_nn(arr, int(self.cfg.scale_factor))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        shifted = np.zeros_like(gray)
        shifted[1:, 1:] = gray[:-1, :-1]
        diff = cv2.subtract(gray, (shifted // 2).astype(np.uint8))

        th = self._threshold(diff)
        th = cv2.medianBlur(th, 3)
        return Image.fromarray(th, mode="L")

    def _pass_d(self, img: Image.Image) -> Image.Image:
        arr = self._to_np_rgb(img)
        arr = self._upscale_nn(arr, int(self.cfg.scale_factor))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        gray = cv2.bilateralFilter(gray, 7, 50, 50)
        th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 7)
        return Image.fromarray(th, mode="L")

    def _tesseract(self, img: Image.Image) -> tuple[str, float]:
        lang = self.cfg.lang
        cfg = f"--oem {int(self.cfg.oem)} --psm {int(self.cfg.psm)}"
        if self.cfg.whitelist:
            cfg += f" -c tessedit_char_whitelist={self.cfg.whitelist}"
        if self.cfg.tessdata_dir:
            cfg += f' --tessdata-dir "{self.cfg.tessdata_dir}"'

        data = pytesseract.image_to_data(img, lang=lang, config=cfg, output_type=pytesseract.Output.DICT)

        words = []
        confs = []
        n = len(data.get("text", []))
        for i in range(n):
            txt = (data["text"][i] or "").strip()
            try:
                c = float(data["conf"][i])
            except Exception:
                c = -1.0
            if txt:
                words.append(txt)
            if c >= 0:
                confs.append(c)

        text = " ".join(words).strip()
        conf = float(sum(confs) / max(1, len(confs))) if confs else -1.0
        return text, conf
