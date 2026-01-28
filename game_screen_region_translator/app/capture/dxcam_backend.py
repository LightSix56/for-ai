from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np
from PIL import Image


class DXCamBackend:
    name = "dxcam"

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        try:
            import dxcam
        except Exception as e:
            raise RuntimeError("dxcam is not installed or failed to import") from e

        self._dxcam_mod = dxcam
        self._cam = dxcam.create()
        if self._cam is None:
            raise RuntimeError("dxcam.create() returned None")

    def grab(self, region: Tuple[int, int, int, int]) -> Image.Image:
        left, top, width, height = region
        r = (left, top, left + width, top + height)
        frame = self._cam.grab(region=r)
        if frame is None:
            raise RuntimeError("dxcam.grab() returned None")

        arr = np.array(frame, dtype=np.uint8)

        if arr.ndim == 3 and arr.shape[2] >= 3:
            rgb = arr[:, :, :3]
        else:
            raise RuntimeError(f"dxcam frame has unexpected shape: {arr.shape}")

        return Image.fromarray(rgb, mode="RGB")
