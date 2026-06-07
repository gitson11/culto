"""Logger centralizado do Culto LouveApp Manager.

Registra eventos em data/app.log com rotação e no console.
Nunca loga senhas ou credenciais.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from src.config import LOG_PATH

_logger: logging.Logger | None = None


def setup_logger() -> logging.Logger:
    """Configura e retorna o logger da aplicação."""
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("culto_app")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Arquivo com rotação (5 MB, 3 backups)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(
        LOG_PATH,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console (apenas INFO+)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """Retorna o logger já configurado ou configura um novo."""
    global _logger
    if _logger is None:
        return setup_logger()
    return _logger
