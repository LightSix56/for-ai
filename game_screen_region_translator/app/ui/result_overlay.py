from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from app.config import OverlayConfig
from app.ui.win_clickthrough import set_clickthrough


class ResultOverlay(QWidget):
    closed = Signal()

    def __init__(self, logger: logging.Logger, overlay_cfg: OverlayConfig):
        super().__init__(None)
        self.logger = logger
        self.cfg = overlay_cfg
        self._rect: Optional[QRect] = None

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.title = QLabel("")
        self.title.setStyleSheet("color: rgba(255,255,255,210); font-weight: 600;")
        self.title.setWordWrap(True)

        self.label = QLabel("")
        self.label.setStyleSheet("color: rgba(255,255,255,235);")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.debug = QLabel("")
        self.debug.setStyleSheet("color: rgba(255,255,255,120); font-size: 11px;")
        self.debug.setWordWrap(True)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        self.v = QVBoxLayout(content)
        self.v.setContentsMargins(self.cfg.padding_px, self.cfg.padding_px, self.cfg.padding_px, self.cfg.padding_px)
        self.v.setSpacing(6)
        self.v.addWidget(self.title)
        self.v.addWidget(self.label)
        self.v.addWidget(self.debug)

        self.scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.scroll)

        self._clickthrough = False

    def current_rect_logical(self) -> QRect:
        return self._rect or QRect(100, 100, 400, 200)

    def set_clickthrough(self, enabled: bool) -> None:
        self._clickthrough = enabled
        self.setAttribute(Qt.WA_TransparentForMouseEvents, enabled)
        try:
            hwnd = int(self.winId())
            set_clickthrough(hwnd, enabled)
        except Exception:
            pass

    def show_status(self, rect: QRect, text: str) -> None:
        self._rect = rect
        self._apply_rect(rect)
        self.title.setText("")
        self.label.setText(text)
        self.debug.setText("")
        self._auto_font()
        self.show()

    def show_text(self, rect: QRect, title: str, text: str, debug_hint: str = "") -> None:
        self._rect = rect
        self._apply_rect(rect)
        self.title.setText(title)
        self.label.setText(text)
        self.debug.setText(debug_hint)
        self._auto_font()
        self.show()

    def _apply_rect(self, rect: QRect) -> None:
        r = QRect(rect)
        if r.width() > self.cfg.max_width_px:
            r.setWidth(self.cfg.max_width_px)
        if r.height() > self.cfg.max_height_px:
            r.setHeight(self.cfg.max_height_px)
        self.setGeometry(r)

    def _auto_font(self) -> None:
        base = int(self.cfg.base_font_size)
        label = self.label

        for size in range(base, int(self.cfg.min_font_size) - 1, -1):
            f = QFont()
            f.setPointSize(size)
            label.setFont(f)

            fm = QFontMetrics(f)
            h = fm.boundingRect(self.label.text() or "A").height()
            rect = self.geometry()
            max_h = rect.height() - 2 * int(self.cfg.padding_px)
            if h * 3 < max_h:
                break

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.closed.emit()
            self.close()
