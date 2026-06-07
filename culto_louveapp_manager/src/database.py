"""Banco de dados SQLite do Culto LouveApp Manager.

Gerencia tabelas: worship_bulletins, worship_people, louveapp_schedules, import_logs.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import DB_PATH
from src.logger import get_logger
from src.models import ImportResult, LouveAppSchedule, WorshipBulletin, WorshipPerson

logger = get_logger()

# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------


def _connect() -> sqlite3.Connection:
    """Abre conexão SQLite com row_factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS worship_bulletins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_text TEXT,
    dirigente TEXT,
    preludio_musica TEXT,
    preludio_cantor TEXT,
    preludio_tom TEXT,
    musica1 TEXT,
    cantor1 TEXT,
    tom1 TEXT,
    ref1 TEXT,
    texto1 TEXT,
    musica2 TEXT,
    cantor2 TEXT,
    tom2 TEXT,
    ref2 TEXT,
    texto2 TEXT,
    musica3 TEXT,
    cantor3 TEXT,
    tom3 TEXT,
    ref3 TEXT,
    texto3 TEXT,
    oracao_louvor TEXT,
    ref_louvor TEXT,
    texto_louvor TEXT,
    ofertas_ref TEXT,
    ofertas_texto TEXT,
    ofertas_oracao TEXT,
    musica4 TEXT,
    cantor4 TEXT,
    tom4 TEXT,
    musica5 TEXT,
    cantor5 TEXT,
    tom5 TEXT,
    oracao_intercessao TEXT,
    pregador TEXT,
    musica_pao TEXT,
    cantor_pao TEXT,
    tom_pao TEXT,
    musica_vinho TEXT,
    cantor_vinho TEXT,
    tom_vinho TEXT,
    musica_extra TEXT,
    cantor_extra TEXT,
    tom_extra TEXT,
    musica_final TEXT,
    cantor_final TEXT,
    tom_final TEXT,
    source TEXT,
    raw_json TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS worship_people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    active INTEGER DEFAULT 1,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS louveapp_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    title TEXT,
    date_text TEXT,
    time_text TEXT,
    ministry TEXT,
    role TEXT,
    person_name TEXT,
    people_text TEXT,
    raw_text TEXT,
    page_url TEXT,
    raw_json TEXT,
    imported_at TEXT
);

CREATE TABLE IF NOT EXISTS import_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    status TEXT,
    message TEXT,
    created_at TEXT
);
"""


def init_db() -> None:
    """Cria as tabelas se não existirem."""
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
        logger.info("Banco de dados inicializado em %s", DB_PATH)
    except Exception as exc:
        logger.error("Erro ao inicializar banco: %s", exc)
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Boletins - CRUD
# ---------------------------------------------------------------------------


def insert_bulletin(b: WorshipBulletin) -> int:
    """Insere boletim e retorna o ID."""
    conn = _connect()
    try:
        fields = WorshipBulletin.DB_FIELDS
        placeholders = ", ".join(["?"] * len(fields))
        cols = ", ".join(fields)
        values = tuple(getattr(b, f, "") or "" for f in fields)
        cur = conn.execute(
            f"INSERT INTO worship_bulletins ({cols}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        logger.info("Boletim inserido: id=%d, data=%s", cur.lastrowid, b.date_text)
        return cur.lastrowid
    except Exception as exc:
        logger.error("Erro ao inserir boletim: %s", exc)
        raise
    finally:
        conn.close()


def update_bulletin(b: WorshipBulletin) -> None:
    """Atualiza boletim existente pelo ID."""
    if not b.id:
        raise ValueError("Boletim sem ID para atualização.")
    conn = _connect()
    try:
        b.updated_at = datetime.now().isoformat(timespec="seconds")
        fields = WorshipBulletin.DB_FIELDS
        set_clause = ", ".join(f"{f} = ?" for f in fields)
        values = tuple(getattr(b, f, "") or "" for f in fields)
        conn.execute(
            f"UPDATE worship_bulletins SET {set_clause} WHERE id = ?",
            (*values, b.id),
        )
        conn.commit()
        logger.info("Boletim atualizado: id=%d, data=%s", b.id, b.date_text)
    except Exception as exc:
        logger.error("Erro ao atualizar boletim: %s", exc)
        raise
    finally:
        conn.close()


def delete_bulletin(bulletin_id: int) -> None:
    """Exclui boletim pelo ID."""
    conn = _connect()
    try:
        conn.execute("DELETE FROM worship_bulletins WHERE id = ?", (bulletin_id,))
        conn.commit()
        logger.info("Boletim excluído: id=%d", bulletin_id)
    except Exception as exc:
        logger.error("Erro ao excluir boletim: %s", exc)
        raise
    finally:
        conn.close()


def _row_to_bulletin(row: sqlite3.Row) -> WorshipBulletin:
    """Converte uma Row SQLite em WorshipBulletin."""
    d = dict(row)
    return WorshipBulletin(
        id=d.pop("id"),
        **{k: (v or "") for k, v in d.items() if k in WorshipBulletin.DB_FIELDS},
    )


def search_by_date(date_text: str) -> list[WorshipBulletin]:
    """Pesquisa boletins por data (busca parcial)."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM worship_bulletins WHERE date_text LIKE ? ORDER BY date_text",
            (f"%{date_text}%",),
        ).fetchall()
        return [_row_to_bulletin(r) for r in rows]
    finally:
        conn.close()


def get_bulletin_by_id(bulletin_id: int) -> Optional[WorshipBulletin]:
    """Busca boletim pelo ID."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM worship_bulletins WHERE id = ?", (bulletin_id,)
        ).fetchone()
        return _row_to_bulletin(row) if row else None
    finally:
        conn.close()


def list_all_bulletins() -> list[WorshipBulletin]:
    """Lista todos os boletins ordenados por data."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM worship_bulletins ORDER BY date_text DESC"
        ).fetchall()
        return [_row_to_bulletin(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Pessoas do Louvor
# ---------------------------------------------------------------------------


def insert_person(name: str) -> int:
    """Insere pessoa (ignora duplicata pelo nome)."""
    conn = _connect()
    try:
        now = datetime.now().isoformat(timespec="seconds")
        cur = conn.execute(
            "INSERT OR IGNORE INTO worship_people (name, active, created_at) VALUES (?, 1, ?)",
            (name.strip(), now),
        )
        conn.commit()
        return cur.lastrowid
    except Exception as exc:
        logger.error("Erro ao inserir pessoa: %s", exc)
        raise
    finally:
        conn.close()


def update_person(person_id: int, name: str) -> None:
    """Atualiza nome de uma pessoa."""
    conn = _connect()
    try:
        conn.execute(
            "UPDATE worship_people SET name = ? WHERE id = ?",
            (name.strip(), person_id),
        )
        conn.commit()
    finally:
        conn.close()


def toggle_person_active(person_id: int) -> None:
    """Alterna ativo/inativo."""
    conn = _connect()
    try:
        conn.execute(
            "UPDATE worship_people SET active = CASE WHEN active = 1 THEN 0 ELSE 1 END WHERE id = ?",
            (person_id,),
        )
        conn.commit()
    finally:
        conn.close()


def list_people(active_only: bool = False) -> list[WorshipPerson]:
    """Lista pessoas do louvor."""
    conn = _connect()
    try:
        q = "SELECT * FROM worship_people"
        if active_only:
            q += " WHERE active = 1"
        q += " ORDER BY name"
        rows = conn.execute(q).fetchall()
        return [
            WorshipPerson(id=r["id"], name=r["name"], active=r["active"], created_at=r["created_at"])
            for r in rows
        ]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Escalas LouveApp
# ---------------------------------------------------------------------------


def save_louveapp_schedules(schedules: list[LouveAppSchedule]) -> int:
    """Salva escalas evitando duplicatas. Retorna quantidade inserida."""
    conn = _connect()
    inserted = 0
    try:
        for s in schedules:
            # Checa duplicata
            existing = conn.execute(
                "SELECT id FROM louveapp_schedules WHERE date_text = ? AND person_name = ? AND role = ?",
                (s.date_text, s.person_name, s.role),
            ).fetchone()
            if existing:
                continue
            conn.execute(
                """INSERT INTO louveapp_schedules
                   (category, title, date_text, time_text, ministry, role,
                    person_name, people_text, raw_text, page_url, raw_json, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    s.category, s.title, s.date_text, s.time_text,
                    s.ministry, s.role, s.person_name, s.people_text,
                    s.raw_text, s.page_url, s.raw_json, s.imported_at,
                ),
            )
            inserted += 1
        conn.commit()
        logger.info("Escalas LouveApp salvas: %d novas de %d total", inserted, len(schedules))
        return inserted
    except Exception as exc:
        logger.error("Erro ao salvar escalas: %s", exc)
        raise
    finally:
        conn.close()


def list_louveapp_schedules() -> list[LouveAppSchedule]:
    """Lista todas as escalas importadas."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM louveapp_schedules ORDER BY date_text DESC"
        ).fetchall()
        return [
            LouveAppSchedule(**{k: (dict(r)[k] or "") for k in dict(r) if k != "id"}, id=r["id"])
            for r in rows
        ]
    finally:
        conn.close()


def clear_louveapp_schedules() -> int:
    """Remove todas as escalas importadas. Retorna quantidade removida."""
    conn = _connect()
    try:
        count = conn.execute("SELECT COUNT(*) FROM louveapp_schedules").fetchone()[0]
        conn.execute("DELETE FROM louveapp_schedules")
        conn.commit()
        logger.info("Escalas LouveApp removidas: %d", count)
        return count
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Log de importações
# ---------------------------------------------------------------------------


def log_import(source: str, status: str, message: str) -> None:
    """Registra uma importação no log do banco."""
    conn = _connect()
    try:
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO import_logs (source, status, message, created_at) VALUES (?, ?, ?, ?)",
            (source, status, message, now),
        )
        conn.commit()
    except Exception:
        pass  # Não propagar erro de log
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------


def get_dashboard_stats() -> dict:
    """Retorna estatísticas para o dashboard."""
    conn = _connect()
    try:
        total_bulletins = conn.execute("SELECT COUNT(*) FROM worship_bulletins").fetchone()[0]
        total_people = conn.execute("SELECT COUNT(*) FROM worship_people WHERE active = 1").fetchone()[0]
        total_schedules = conn.execute("SELECT COUNT(*) FROM louveapp_schedules").fetchone()[0]

        last_bulletin = conn.execute(
            "SELECT date_text FROM worship_bulletins ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        last_import = conn.execute(
            "SELECT source, created_at FROM import_logs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

        return {
            "total_bulletins": total_bulletins,
            "total_people": total_people,
            "total_schedules": total_schedules,
            "last_bulletin": last_bulletin["date_text"] if last_bulletin else "Nenhum",
            "last_import_source": last_import["source"] if last_import else "Nenhuma",
            "last_import_date": last_import["created_at"] if last_import else "—",
        }
    finally:
        conn.close()
