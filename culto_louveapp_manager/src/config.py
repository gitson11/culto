"""Configuração centralizada do Culto LouveApp Manager.

Carrega variáveis do .env e define caminhos do projeto.
Credenciais são validadas apenas quando o usuário solicita importação do LouveApp.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Caminhos do projeto
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
DEBUG_DIR = DATA_DIR / "debug"
LEGACY_DIR = BASE_DIR / "legacy"
DB_PATH = DATA_DIR / "culto.sqlite3"
LOG_PATH = DATA_DIR / "app.log"

# Garante que os diretórios existam
for _dir in (DATA_DIR, OUTPUT_DIR, DEBUG_DIR, LEGACY_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Carrega .env (silenciosamente se não existir)
# ---------------------------------------------------------------------------

_env_path = BASE_DIR / ".env"
load_dotenv(_env_path, override=False)

# ---------------------------------------------------------------------------
# Configurações de navegador
# ---------------------------------------------------------------------------

HEADLESS: bool = os.getenv("HEADLESS", "false").strip().lower() in ("true", "1", "yes")
SLOW_MO_MS: int = int(os.getenv("SLOW_MO_MS", "150"))

# ---------------------------------------------------------------------------
# Credenciais (leitura segura)
# ---------------------------------------------------------------------------


def get_credentials() -> tuple[str | None, str | None]:
    """Retorna (email, password) do .env ou (None, None) se ausentes."""
    email = os.getenv("LOUVEAPP_EMAIL")
    password = os.getenv("LOUVEAPP_PASSWORD")
    return email, password


def validate_credentials() -> tuple[str, str]:
    """Valida e retorna credenciais. Levanta ValueError se ausentes ou vazias."""
    email, password = get_credentials()
    if not email or not email.strip():
        raise ValueError(
            "LOUVEAPP_EMAIL não configurado.\n"
            "Crie o arquivo .env a partir de .env.example e preencha suas credenciais."
        )
    if not password or not password.strip() or password.strip() == "coloque_sua_senha_aqui":
        raise ValueError(
            "LOUVEAPP_PASSWORD não configurado.\n"
            "Edite o arquivo .env e coloque sua senha real do LouveApp."
        )
    return email.strip(), password.strip()


def get_legacy_xlsm_path() -> Path | None:
    """Procura o arquivo .xlsm legado na pasta legacy/."""
    # Primeiro tenta o nome exato
    exact = LEGACY_DIR / "BOLETIM_VBA_CORRIGIDO.xlsm"
    if exact.exists():
        return exact
    # Senão, procura qualquer .xlsm
    xlsm_files = list(LEGACY_DIR.glob("*.xlsm"))
    if xlsm_files:
        return xlsm_files[0]
    return None
