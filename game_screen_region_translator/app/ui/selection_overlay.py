from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QWidget, QApplication


class SelectionOverlay(QWidget):
    cancelled = Signal()
    region_selected = Signal(QRect)

    def __init__(self, logger: logging.Logger):
        super().__init__(None)
        self.logger = logger

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self._start = None
        self._current = None

    def show_on_all_screens(self) -> None:
        rect = QApplication.primaryScreen().virtualGeometry()
        if len(QApplication.screens()) > 1:
            for s in QApplication.screens():
                rect = rect.united(s.virtualGeometry())
        self.setGeometry(rect)
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start = event.pos()
            self._current = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self._start is not None:
            self._current = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._start is not None:
            end = event.pos()
            x1, y1 = self._start.x(), self._start.y()
            x2, y2 = end.x(), end.y()
            if x1 > x2:
                x1, x2 = x2, x1
            if y1 > y2:
                y1, y2 = y2, y1
            rect = QRect(x1, y1, x2 - x1, y2 - y1)
            if rect.width() > 10 and rect.height() > 10:
                self.region_selected.emit(rect)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._start and self._current:
            x1, y1 = self._start.x(), self._start.y()
            x2, y2 = self._current.x(), self._current.y()
            if x1 > x2:
                x1, x2 = x2, x1
            if y1 > y2:
                y1, y2 = y2, y1
            rect = QRect(x1, y1, x2 - x1, y2 - y1)
            painter.fillRect(rect, QColor(0, 0, 0, 0))
            painter.drawRect(rect)
            painter.drawRect(rect.adjusted(-2, -2, 2, 2))
