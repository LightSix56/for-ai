from __future__ import annotations

import logging
import traceback

from PySide6.QtCore import QObject, QThread, Signal


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, logger: logging.Logger):
        super().__init__()
        self.fn = fn
        self.logger = logger
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self._run)

    def start(self):
        self.thread.start()

    def _run(self):
        try:
            res = self.fn()
            self.finished.emit(res)
        except Exception as e:
            self.logger.exception("Worker failed")
            self.failed.emit(str(e))
        finally:
            self.thread.quit()
            self.thread.wait(2000)
