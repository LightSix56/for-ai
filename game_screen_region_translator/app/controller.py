from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple

from dotenv import load_dotenv
from PIL import Image
from PySide6.QtCore import QObject, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication

from app.config import AppConfig
from app.hotkey import HotkeyManager, HotkeySpec, hotkey_from_string
from app.ui.tray import Tray
from app.ui.selection_overlay import SelectionOverlay
from app.ui.result_overlay import ResultOverlay
from app.ui.worker import Worker
from app.capture.capture_manager import CaptureManager
from app.ocr.pipeline import OcrPipeline, OcrResult
from app.translate.base import TranslatorProvider
from app.translate.deepl_provider import DeepLTranslator
from app.translate.libre_provider import LibreTranslator
from app.translate.cache import CachedTranslator


class AppState(Enum):
    IDLE = auto()
    SELECTION = auto()
    PROCESSING = auto()
    RESULT = auto()


@dataclass
class SelectedRegion:
    rect_logical: QRect
    rect_physical: Tuple[int, int, int, int]


class AppController(QObject):
    request_toggle = Signal()
    request_close = Signal()

    def __init__(self, cfg: AppConfig, logger: logging.Logger):
        super().__init__()
        self.cfg = cfg
        self.logger = logger

        load_dotenv()

        self.state = AppState.IDLE

        self.tray: Optional[Tray] = None
        self.selection_overlay: Optional[SelectionOverlay] = None
        self.result_overlay: Optional[ResultOverlay] = None

        self.hk = HotkeyManager(logger=self.logger)
        self.hk.activated.connect(self._on_hotkey_activated)

        self.capture = CaptureManager(cfg.capture, logger=self.logger)
        self.ocr = OcrPipeline(cfg.ocr, logger=self.logger)

        self.translator = self._build_translator()

        self.worker: Optional[Worker] = None
        self._busy = False

        self._config_path = "config.json"

        self.request_toggle.connect(self.toggle_flow)
        self.request_close.connect(self.close_overlay)

    def _build_translator(self) -> TranslatorProvider:
        prov = self.cfg.translation.provider.lower().strip()
        if prov == "libre":
            base = LibreTranslator(self.cfg.translation.libre, self.logger)
        else:
            base = DeepLTranslator(self.cfg.translation.deepl, self.logger)

        return CachedTranslator(
            base=base,
            ttl_sec=self.cfg.translation.cache_ttl_sec,
            logger=self.logger,
        )

    def start(self) -> None:
        self.logger.info("App start. State=IDLE")
        self.tray = Tray(
            on_toggle=self.toggle_flow,
            on_change_hotkey=self.open_hotkey_dialog,
            on_toggle_clickthrough=self.toggle_clickthrough,
            on_quit=self.quit_app,
            logger=self.logger,
        )
        self.tray.set_clickthrough_checked(self.cfg.overlay.click_through)
        self.tray.show()

        self._register_hotkeys()

        self._heartbeat = QTimer()
        self._heartbeat.start(1000)
        self._heartbeat.timeout.connect(lambda: None)

    def shutdown(self) -> None:
        self.logger.info("Shutdown requested")
        try:
            self.hk.unregister_all()
        except Exception:
            pass
        try:
            self._destroy_selection()
            self._destroy_result()
        except Exception:
            pass
        self.logger.info("Shutdown complete")

    def quit_app(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def _register_hotkeys(self) -> None:
        self.hk.unregister_all()

        toggle = hotkey_from_string(self.cfg.hotkeys.toggle)
        close = hotkey_from_string(self.cfg.hotkeys.close)

        self.hk.register(1, toggle)
        self.hk.register(2, close)

        self.logger.info(f"Registered hotkeys: toggle={self.cfg.hotkeys.toggle}, close={self.cfg.hotkeys.close}")

    def open_hotkey_dialog(self) -> None:
        if not self.tray:
            return
        new_hotkey = self.tray.open_hotkey_dialog(current=self.cfg.hotkeys.toggle)
        if not new_hotkey:
            return

        old = self.cfg.hotkeys.toggle
        self.cfg.hotkeys.toggle = new_hotkey
        try:
            self._register_hotkeys()
            self.cfg.save(self._config_path)
            self.tray.notify("Hotkey updated", f"New toggle hotkey: {new_hotkey}")
        except Exception as e:
            self.cfg.hotkeys.toggle = old
            self._register_hotkeys()
            self.tray.notify("Hotkey error", f"Failed to set hotkey: {e}")

    def toggle_clickthrough(self) -> None:
        self.cfg.overlay.click_through = not self.cfg.overlay.click_through
        self.cfg.save(self._config_path)
        if self.tray:
            self.tray.set_clickthrough_checked(self.cfg.overlay.click_through)
            self.tray.notify("Overlay", f"Click-through: {self.cfg.overlay.click_through}")

        if self.result_overlay:
            self.result_overlay.set_clickthrough(self.cfg.overlay.click_through)

    def _on_hotkey_activated(self, hotkey_id: int) -> None:
        if hotkey_id == 1:
            self.request_toggle.emit()
        elif hotkey_id == 2:
            self.request_close.emit()

    def toggle_flow(self) -> None:
        if self.state in (AppState.RESULT, AppState.PROCESSING):
            self.close_overlay()
            if self._busy:
                return

        if self.state == AppState.SELECTION:
            self.logger.info("Toggle in selection -> cancel")
            self._cancel_selection()
            return

        if self.state == AppState.IDLE:
            self.logger.info("Hotkey -> enter selection")
            self._enter_selection_mode()

    def close_overlay(self) -> None:
        if self.state in (AppState.RESULT, AppState.PROCESSING):
            self.logger.info("Close overlay requested")
            self._busy = False
            self._destroy_result()
            self.state = AppState.IDLE
            self.logger.info("State=IDLE")

    def _enter_selection_mode(self) -> None:
        self._destroy_result()
        self._destroy_selection()

        self.selection_overlay = SelectionOverlay(logger=self.logger)
        self.selection_overlay.cancelled.connect(self._on_selection_cancelled)
        self.selection_overlay.region_selected.connect(self._on_region_selected)
        self.selection_overlay.show_on_all_screens()

        self.state = AppState.SELECTION
        self.logger.info("State=SELECTION")

    def _cancel_selection(self) -> None:
        self._destroy_selection()
        self.state = AppState.IDLE
        self.logger.info("State=IDLE")

    def _on_selection_cancelled(self) -> None:
        self.logger.info("Selection cancelled (Esc)")
        self._cancel_selection()

    def _on_region_selected(self, rect_logical: QRect) -> None:
        self.logger.info(f"Selection -> rect_logical={rect_logical.getRect()}")
        self._destroy_selection()

        region = self._compute_physical_region(rect_logical)
        self.logger.info(f"Capture rect_physical={region.rect_physical}")

        self._show_processing_overlay(rect_logical, "OCR…")

        self.state = AppState.PROCESSING
        self._busy = True
        self.logger.info("State=PROCESSING")

        self.worker = Worker(
            fn=lambda: self._process(region),
            logger=self.logger,
        )
        self.worker.finished.connect(self._on_processing_done)
        self.worker.failed.connect(self._on_processing_failed)
        self.worker.start()

    def _compute_physical_region(self, rect_logical: QRect) -> SelectedRegion:
        center = rect_logical.center()
        screen = QGuiApplication.screenAt(center)
        if screen is None:
            screen = QGuiApplication.primaryScreen()

        dpr = float(screen.devicePixelRatio() or 1.0)

        left = int(round(rect_logical.left() * dpr))
        top = int(round(rect_logical.top() * dpr))
        width = int(round(rect_logical.width() * dpr))
        height = int(round(rect_logical.height() * dpr))

        return SelectedRegion(rect_logical=rect_logical, rect_physical=(left, top, width, height))

    def _show_processing_overlay(self, rect_logical: QRect, text: str) -> None:
        self._destroy_result()
        self.result_overlay = ResultOverlay(
            logger=self.logger,
            overlay_cfg=self.cfg.overlay,
        )
        self.result_overlay.closed.connect(self.close_overlay)
        self.result_overlay.set_clickthrough(False)
        self.result_overlay.show_status(rect_logical, text)

    def _process(self, region: SelectedRegion) -> tuple[str, str, OcrResult]:
        self.logger.info("Capture -> start")
        pil_img: Image.Image = self.capture.grab(region.rect_physical)
        self.logger.info(f"Capture -> ok size={pil_img.size}")

        self.logger.info("OCR -> start")
        ocr_res = self.ocr.run(pil_img)
        self.logger.info(f"OCR -> best_pass={ocr_res.best_pass} conf={ocr_res.best_conf:.1f} text_len={len(ocr_res.text)}")

        text_en = ocr_res.text.strip()
        if not text_en:
            raise RuntimeError("OCR returned empty text")

        self.logger.info("Translate -> start")
        text_ru = self.translator.translate(text_en, source_lang="EN", target_lang="RU", max_chars_per_chunk=self.cfg.translation.max_chars_per_chunk)
        self.logger.info(f"Translate -> ok text_len={len(text_ru)}")

        return text_en, text_ru, ocr_res

    def _on_processing_done(self, payload: object) -> None:
        if not self._busy:
            return
        self._busy = False

        text_en, text_ru, ocr_res = payload
        self.logger.info("Processing -> done")

        if not self.result_overlay:
            self.state = AppState.IDLE
            return

        self.result_overlay.set_clickthrough(self.cfg.overlay.click_through)

        self.result_overlay.show_text(
            rect=self.result_overlay.current_rect_logical(),
            title="EN → RU",
            text=text_ru,
            debug_hint=f"OCR pass={ocr_res.best_pass}, conf={ocr_res.best_conf:.1f}",
        )
        self.state = AppState.RESULT
        self.logger.info("State=RESULT")

    def _on_processing_failed(self, err: str) -> None:
        if not self._busy:
            return
        self._busy = False

        self.logger.error(f"Processing -> failed: {err}")

        if self.result_overlay:
            self.result_overlay.set_clickthrough(False)
            self.result_overlay.show_text(
                rect=self.result_overlay.current_rect_logical(),
                title="Error",
                text=err,
                debug_hint="",
            )
            self.state = AppState.RESULT
        else:
            self.state = AppState.IDLE

    def _destroy_selection(self) -> None:
        if self.selection_overlay:
            self.selection_overlay.close()
            self.selection_overlay.deleteLater()
            self.selection_overlay = None

    def _destroy_result(self) -> None:
        if self.result_overlay:
            self.result_overlay.close()
            self.result_overlay.deleteLater()
            self.result_overlay = None

    def _cancel_processing(self) -> None:
        self._busy = False
