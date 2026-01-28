from __future__ import annotations

import logging
from typing import Callable, Optional

from PySide6.QtGui import QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QSystemTrayIcon,
    QMessageBox,
    QInputDialog,
    QWidget,
)


class Tray:
    def __init__(
        self,
        on_toggle: Callable[[], None],
        on_change_hotkey: Callable[[], None],
        on_toggle_clickthrough: Callable[[], None],
        on_quit: Callable[[], None],
        logger: logging.Logger,
    ):
        self.logger = logger
        self.on_toggle = on_toggle
        self.on_change_hotkey = on_change_hotkey
        self.on_toggle_clickthrough = on_toggle_clickthrough
        self.on_quit = on_quit

        self._widget = QWidget()
        self.tray = QSystemTrayIcon(self._widget)
        self.tray.setToolTip("Game Screen Region Translator")

        self.menu = QMenu()
        self._clickthrough_action = None
        self._setup_menu()
        self.tray.setContextMenu(self.menu)

    def _setup_menu(self):
        action_toggle = self.menu.addAction("Toggle (Test)")
        action_toggle.triggered.connect(self.on_toggle)

        action_hotkey = self.menu.addAction("Change Hotkey…")
        action_hotkey.triggered.connect(self.on_change_hotkey)

        self.menu.addSeparator()

        self._clickthrough_action = self.menu.addAction("Click-through mode")
        self._clickthrough_action.setCheckable(True)
        self._clickthrough_action.triggered.connect(self.on_toggle_clickthrough)

        self.menu.addSeparator()

        action_quit = self.menu.addAction("Quit")
        action_quit.triggered.connect(self.on_quit)

    def show(self):
        self.tray.show()

    def set_clickthrough_checked(self, enabled: bool):
        if self._clickthrough_action:
            self._clickthrough_action.setChecked(enabled)

    def open_hotkey_dialog(self, current: str = "") -> Optional[str]:
        text, ok = QInputDialog.getText(
            self._widget,
            "Change Hotkey",
            "Enter new hotkey (e.g., CTRL+SHIFT+T):",
            text=current,
        )
        if ok and text.strip():
            return text.strip().upper()
        return None

    def notify(self, title: str, message: str):
        self.tray.showMessage(title, message, QSystemTrayIcon.NoIcon, 3000)
