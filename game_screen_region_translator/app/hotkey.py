from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import logging
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, QAbstractNativeEventFilter
from PySide6.QtWidgets import QApplication


# Важно: use_last_error=True, иначе ctypes.get_last_error() часто будет 0. [web:385][web:387]
user32 = ctypes.WinDLL("user32", use_last_error=True)

WM_HOTKEY = 0x0312

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


# Прототипы WinAPI (чтобы ctypes корректно маршалил типы)
user32.RegisterHotKey.argtypes = (wt.HWND, wt.INT, wt.UINT, wt.UINT)
user32.RegisterHotKey.restype = wt.BOOL

user32.UnregisterHotKey.argtypes = (wt.HWND, wt.INT)
user32.UnregisterHotKey.restype = wt.BOOL


@dataclass(frozen=True)
class HotkeySpec:
    modifiers: int
    vk: int


class MSG(ctypes.Structure):
    # MSG в WinAPI содержит ещё lPrivate; пусть будет, хуже не станет.
    _fields_ = [
        ("hwnd", wt.HWND),
        ("message", wt.UINT),
        ("wParam", wt.WPARAM),
        ("lParam", wt.LPARAM),
        ("time", wt.DWORD),
        ("pt", wt.POINT),
        ("lPrivate", wt.DWORD),
    ]


def _ptr_to_int(ptr) -> int:
    # PySide6 передаёт void pointer-объект; обычно int(ptr) работает.
    # Делаем максимально терпимо к типам.
    if isinstance(ptr, int):
        return ptr
    try:
        return int(ptr)
    except TypeError:
        # иногда бывает объект с .__int__ или .value
        v = getattr(ptr, "value", None)
        if isinstance(v, int):
            return v
        raise


class HotkeyEventFilter(QAbstractNativeEventFilter):
    def __init__(self, manager: "HotkeyManager"):
        super().__init__()
        self.manager = manager

    # В Qt/PySide6: если хочешь "съесть" событие — верни True, иначе False. [web:403]
    def nativeEventFilter(self, eventType, message):
        try:
            et = bytes(eventType)
            if et in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
                addr = _ptr_to_int(message)
                msg = ctypes.cast(ctypes.c_void_p(addr), ctypes.POINTER(MSG)).contents

                if msg.message == WM_HOTKEY:
                    hotkey_id = int(msg.wParam)
                    self.manager.activated.emit(hotkey_id)
                    return True, 0
        except Exception as e:
            self.manager._logger.exception(f"nativeEventFilter error: {e}")

        return False, 0


class HotkeyManager(QObject):
    activated = Signal(int)

    def __init__(self, logger: logging.Logger):
        super().__init__()
        self._logger = logger
        self._registered: dict[int, HotkeySpec] = {}

        self._filter = HotkeyEventFilter(self)
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("QApplication is not created yet")
        app.installNativeEventFilter(self._filter)

    def register(self, hotkey_id: int, spec: HotkeySpec) -> None:
        ok = user32.RegisterHotKey(None, hotkey_id, spec.modifiers | MOD_NOREPEAT, spec.vk)
        if not ok:
            # Так получишь реальную WinAPI-ошибку, а не err=0. [web:385]
            raise ctypes.WinError(ctypes.get_last_error())
        self._registered[hotkey_id] = spec

    def unregister(self, hotkey_id: int) -> None:
        user32.UnregisterHotKey(None, hotkey_id)
        self._registered.pop(hotkey_id, None)

    def unregister_all(self) -> None:
        for hid in list(self._registered.keys()):
            try:
                self.unregister(hid)
            except Exception:
                pass


def hotkey_from_string(s: str) -> HotkeySpec:
    s = (s or "").strip().upper().replace(" ", "")
    parts = [p for p in s.split("+") if p]
    if not parts:
        raise ValueError("Empty hotkey")

    mods = 0
    key = None

    for p in parts:
        if p in ("CTRL", "CONTROL"):
            mods |= MOD_CONTROL
        elif p == "SHIFT":
            mods |= MOD_SHIFT
        elif p == "ALT":
            mods |= MOD_ALT
        elif p in ("WIN", "WINDOWS"):
            mods |= MOD_WIN
        else:
            key = p

    if not key:
        raise ValueError(f"No key in hotkey: {s}")

    vk = _vk_from_key_name(key)
    return HotkeySpec(modifiers=mods, vk=vk)


def _vk_from_key_name(key: str) -> int:
    if len(key) == 1 and key.isalnum():
        return ord(key)

    special = {
        "ESC": 0x1B,
        "ESCAPE": 0x1B,
        "SPACE": 0x20,
        "TAB": 0x09,
        "ENTER": 0x0D,
        "RETURN": 0x0D,
        "BACKSPACE": 0x08,
        "DELETE": 0x2E,
        "INS": 0x2D,
        "INSERT": 0x2D,
        "HOME": 0x24,
        "END": 0x23,
        "PGUP": 0x21,
        "PAGEUP": 0x21,
        "PGDN": 0x22,
        "PAGEDOWN": 0x22,
        "LEFT": 0x25,
        "UP": 0x26,
        "RIGHT": 0x27,
        "DOWN": 0x28,
    }
    if key in special:
        return special[key]

    if key.startswith("F") and key[1:].isdigit():
        n = int(key[1:])
        if 1 <= n <= 24:
            return 0x70 + (n - 1)

    raise ValueError(f"Unsupported key: {key}")
