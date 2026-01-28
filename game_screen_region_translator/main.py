import os
import signal
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.config import AppConfig
from app.controller import AppController
from app.dpi import enable_per_monitor_dpi_awareness
from app.logging_setup import setup_logging


def main():
    enable_per_monitor_dpi_awareness()

    cfg = AppConfig.load("config.json")
    logger = setup_logging(cfg.logging)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    controller = AppController(cfg, logger)
    controller.start()

    def _sigint(*_):
        app.quit()

    signal.signal(signal.SIGINT, _sigint)

    tick = QTimer()
    tick.start(200)
    tick.timeout.connect(lambda: None)

    app.aboutToQuit.connect(controller.shutdown)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
