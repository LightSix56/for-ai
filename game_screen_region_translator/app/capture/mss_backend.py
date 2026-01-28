from __future__ import annotations

import logging
from typing import Tuple

import mss
import numpy as np
from PIL import Image


class MSSBackend:
    name = "mss"

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._mss = mss.mss()

    def grab(self, region: Tuple[int, int, int, int]) -> Image.Image:
        left, top, width, height = region
        mon = {"left": left, "top": top, "width": width, "height": height}
        shot = self._mss.grab(mon)
        arr = np.array(shot, dtype=np.uint8)
        rgb = arr[:, :, :3][:, :, ::-1]
        return Image.fromarray(rgb, mode="RGB")
