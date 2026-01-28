from __future__ import annotations

import ctypes
import ctypes.wintypes as wt

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOOLWINDOW = 0x80

user32 = ctypes.windll.user32


def set_clickthrough(hwnd: int, enabled: bool) -> None:
    if not hwnd:
        return
    style = user32.GetWindowLongW(wt.HWND(hwnd), GWL_EXSTYLE)
    if enabled:
        style |= (WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)
    else:
        style &= ~WS_EX_TRANSPARENT
    user32.SetWindowLongW(wt.HWND(hwnd), GWL_EXSTYLE, style)
