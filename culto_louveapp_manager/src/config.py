from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Tuple

from dotenv import load_dotenv


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
DEBUG_DIR = DATA_DIR / "debug"
LEGACY_DIR = BASE_DIR / "legacy"
TEMPLATES_DIR = BASE_DIR / "templates"
DB_PATH = DATA_DIR / "culto_louveapp.sqlite3"
LEGACY_XLSM_PATH = LEGACY_DIR / "BOLETIM_VBA_CORRIGIDO.xlsm"
ENV_PATH = BASE_DIR / ".env"

LOUVEAPP_LOGIN_URL = "https://app.louveapp.com.br/#/login"


class ConfigError(RuntimeError):
    """Erro de configuracao tratado para exibicao amigavel na interface."""


def ensure_directories() -> None:
    for directory in (DATA_DIR, OUTPUT_DIR, DEBUG_DIR, LEGACY_DIR, TEMPLATES_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def reload_env() -> None:
    load_dotenv(ENV_PATH, override=True)


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


def get_headless() -> bool:
    reload_env()
    return _as_bool(os.getenv("HEADLESS"), False)


def get_slow_mo_ms() -> int:
    reload_env()
    raw_value = os.getenv("SLOW_MO_MS", "150").strip()
    try:
        return max(0, int(raw_value))
    except ValueError:
        return 150


def get_louveapp_credentials() -> Tuple[str, str]:
    reload_env()
    email = os.getenv("LOUVEAPP_EMAIL", "").strip()
    password = os.getenv("LOUVEAPP_PASSWORD", "").strip()
    return email, password


def validate_louveapp_credentials() -> Tuple[str, str]:
    if not ENV_PATH.exists():
        raise ConfigError(
            "Arquivo .env nao encontrado. Crie uma copia de .env.example como .env antes de importar do LouveApp."
        )

    email, password = get_louveapp_credentials()
    if not email:
        raise ConfigError("LOUVEAPP_EMAIL esta vazio no arquivo .env.")
    if not password or password == "coloque_sua_senha_aqui":
        raise ConfigError("LOUVEAPP_PASSWORD esta vazio ou ainda esta com o valor de exemplo.")
    return email, password


ensure_directories()
reload_env()
