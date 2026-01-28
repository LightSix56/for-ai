from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
from PIL import Image

from app.config import CaptureConfig
from app.capture.mss_backend import MSSBackend
from app.capture.dxcam_backend import DXCamBackend


class CaptureManager:
    def __init__(self, cfg: CaptureConfig, logger: logging.Logger):
        self.cfg = cfg
        self.logger = logger

        self.backends = []
        for name in (cfg.backend_order or ["mss", "dxcam"]):
            if name == "mss":
                self.backends.append(MSSBackend(logger))
            elif name == "dxcam":
                try:
                    self.backends.append(DXCamBackend(logger))
                except Exception as e:
                    self.logger.warning(f"DXcam backend unavailable: {e}")

        if not self.backends:
            raise RuntimeError("No capture backends available")

    def grab(self, region: Tuple[int, int, int, int]) -> Image.Image:
        last_err = None
        for i, be in enumerate(self.backends):
            try:
                img = be.grab(region)
                if self._looks_black(img):
                    self.logger.warning(f"Capture backend={be.name} produced near-black frame -> trying fallback")
                    continue
                self.logger.info(f"Capture backend selected: {be.name}")
                return img
            except Exception as e:
                last_err = e
                self.logger.warning(f"Capture backend={be.name} failed: {e}")
                continue
        raise RuntimeError(f"All capture backends failed. Last error: {last_err}")

    def _looks_black(self, img: Image.Image) -> bool:
        arr = np.asarray(img.convert("RGB"), dtype=np.uint8)
        gray = arr.mean(axis=2).astype(np.float32)

        mean = float(gray.mean())
        nonzero_ratio = float((gray > 10).mean())

        if mean < float(self.cfg.black_threshold_mean) and nonzero_ratio < float(self.cfg.black_threshold_nonzero_ratio):
            return True
        return False
