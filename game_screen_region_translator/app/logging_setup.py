import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import LoggingConfig


def setup_logging(cfg: LoggingConfig) -> logging.Logger:
    os.makedirs(os.path.dirname(cfg.file) or ".", exist_ok=True)

    logger = logging.getLogger("gsrt")
    logger.setLevel(getattr(logging, cfg.level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = RotatingFileHandler(cfg.file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
