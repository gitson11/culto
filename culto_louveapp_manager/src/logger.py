from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from src.config import DATA_DIR, ensure_directories


LOG_PATH = DATA_DIR / "app.log"


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage().lower()
        for key in ("LOUVEAPP_PASSWORD", "password", "senha"):
            if key.lower() in message:
                record.msg = "[mensagem removida por conter dado sensivel]"
                record.args = ()
                break
        return True


def setup_logging() -> None:
    ensure_directories()
    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
