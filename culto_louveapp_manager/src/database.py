from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from typing import Iterable, Optional

from src.config import DB_PATH, ensure_directories
from src.logger import get_logger
from src.models import (
    BULLETIN_DB_FIELDS,
    SCHEDULE_DB_FIELDS,
    ImportResult,
    LouveAppSchedule,
    WorshipBulletin,
    WorshipPerson,
    now_text,
)


logger = get_logger(__name__)


BULLETIN_COLUMNS_SQL = """
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
"""


def get_connection() -> sqlite3.Connection:
    ensure_directories()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    Database().create_tables()


class Database:
    def create_tables(self) -> None:
        with closing(get_connection()) as connection, connection:
            connection.execute(f"CREATE TABLE IF NOT EXISTS worship_bulletins ({BULLETIN_COLUMNS_SQL})")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS worship_people (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    active INTEGER DEFAULT 1,
                    created_at TEXT
                )
                """
            )
            connection.execute(
                """
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
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS import_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    status TEXT,
                    message TEXT,
                    created_at TEXT
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_bulletins_date ON worship_bulletins(date_text)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_people_name ON worship_people(name)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_schedules_date ON louveapp_schedules(date_text)")
        logger.info("Banco SQLite pronto em %s", DB_PATH)

    def insert_bulletin(self, bulletin: WorshipBulletin) -> int:
        current_time = now_text()
        if not bulletin.created_at:
            bulletin.created_at = current_time
        bulletin.updated_at = current_time
        if not bulletin.source:
            bulletin.source = "manual"

        data = bulletin.to_db_dict()
        columns = ", ".join(BULLETIN_DB_FIELDS)
        placeholders = ", ".join([f":{field}" for field in BULLETIN_DB_FIELDS])
        try:
            with closing(get_connection()) as connection, connection:
                cursor = connection.execute(
                    f"INSERT INTO worship_bulletins ({columns}) VALUES ({placeholders})",
                    data,
                )
                bulletin_id = int(cursor.lastrowid)
            logger.info("Boletim salvo: id=%s data=%s", bulletin_id, bulletin.date_text)
            return bulletin_id
        except sqlite3.Error:
            logger.exception("Erro ao salvar boletim")
            raise

    def update_bulletin(self, bulletin_id: int, bulletin: WorshipBulletin) -> None:
        bulletin.id = bulletin_id
        bulletin.updated_at = now_text()
        if not bulletin.source:
            bulletin.source = "manual"
        assignments = ", ".join([f"{field} = :{field}" for field in BULLETIN_DB_FIELDS if field != "created_at"])
        data = bulletin.to_db_dict()
        data["id"] = bulletin_id
        try:
            with closing(get_connection()) as connection, connection:
                connection.execute(
                    f"UPDATE worship_bulletins SET {assignments} WHERE id = :id",
                    data,
                )
            logger.info("Boletim atualizado: id=%s", bulletin_id)
        except sqlite3.Error:
            logger.exception("Erro ao atualizar boletim")
            raise

    def delete_bulletin(self, bulletin_id: int) -> None:
        try:
            with closing(get_connection()) as connection, connection:
                connection.execute("DELETE FROM worship_bulletins WHERE id = ?", (bulletin_id,))
            logger.info("Boletim excluido: id=%s", bulletin_id)
        except sqlite3.Error:
            logger.exception("Erro ao excluir boletim")
            raise

    def get_bulletin(self, bulletin_id: int) -> Optional[WorshipBulletin]:
        with closing(get_connection()) as connection:
            row = connection.execute("SELECT * FROM worship_bulletins WHERE id = ?", (bulletin_id,)).fetchone()
        return WorshipBulletin.from_row(row) if row else None

    def find_bulletins_by_date(self, date_text: str) -> list[WorshipBulletin]:
        query = f"%{date_text.strip()}%"
        with closing(get_connection()) as connection:
            rows = connection.execute(
                "SELECT * FROM worship_bulletins WHERE date_text LIKE ? ORDER BY id DESC",
                (query,),
            ).fetchall()
        return [WorshipBulletin.from_row(row) for row in rows]

    def get_bulletin_by_date(self, date_text: str) -> Optional[WorshipBulletin]:
        query = f"%{date_text.strip()}%"
        with closing(get_connection()) as connection:
            row = connection.execute(
                "SELECT * FROM worship_bulletins WHERE date_text LIKE ? ORDER BY id DESC LIMIT 1",
                (query,),
            ).fetchone()
        return WorshipBulletin.from_row(row) if row else None

    def list_bulletins(self) -> list[WorshipBulletin]:
        with closing(get_connection()) as connection:
            rows = connection.execute("SELECT * FROM worship_bulletins ORDER BY id DESC").fetchall()
        return [WorshipBulletin.from_row(row) for row in rows]

    def bulletin_exists(self, source: str, date_text: str, raw_json: str) -> bool:
        with closing(get_connection()) as connection:
            row = connection.execute(
                """
                SELECT id FROM worship_bulletins
                WHERE COALESCE(source, '') = ? AND COALESCE(date_text, '') = ? AND COALESCE(raw_json, '') = ?
                LIMIT 1
                """,
                (source, date_text, raw_json),
            ).fetchone()
        return row is not None

    def save_person(self, name: str, active: int = 1) -> Optional[int]:
        clean_name = " ".join((name or "").strip().split())
        if not clean_name:
            return None
        current_time = now_text()
        try:
            with closing(get_connection()) as connection, connection:
                connection.execute(
                    """
                    INSERT INTO worship_people(name, active, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET active = excluded.active
                    """,
                    (clean_name, active, current_time),
                )
                row = connection.execute("SELECT id FROM worship_people WHERE name = ?", (clean_name,)).fetchone()
            return int(row["id"]) if row else None
        except sqlite3.Error:
            logger.exception("Erro ao salvar pessoa do louvor")
            raise

    def update_person(self, person_id: int, name: str, active: int = 1) -> None:
        clean_name = " ".join((name or "").strip().split())
        if not clean_name:
            raise ValueError("Nome nao pode ficar vazio.")
        try:
            with closing(get_connection()) as connection, connection:
                connection.execute(
                    "UPDATE worship_people SET name = ?, active = ? WHERE id = ?",
                    (clean_name, active, person_id),
                )
            logger.info("Pessoa do louvor atualizada: id=%s", person_id)
        except sqlite3.Error:
            logger.exception("Erro ao atualizar pessoa do louvor")
            raise

    def inactivate_person(self, person_id: int) -> None:
        with closing(get_connection()) as connection, connection:
            connection.execute("UPDATE worship_people SET active = 0 WHERE id = ?", (person_id,))
        logger.info("Pessoa do louvor inativada: id=%s", person_id)

    def list_people(self, search: str = "", active_only: bool = False) -> list[WorshipPerson]:
        clauses = []
        params: list[object] = []
        if search.strip():
            clauses.append("name LIKE ?")
            params.append(f"%{search.strip()}%")
        if active_only:
            clauses.append("active = 1")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with closing(get_connection()) as connection:
            rows = connection.execute(
                f"SELECT * FROM worship_people {where} ORDER BY active DESC, name COLLATE NOCASE",
                params,
            ).fetchall()
        return [WorshipPerson.from_row(row) for row in rows]

    def schedule_exists(self, schedule: LouveAppSchedule) -> bool:
        with closing(get_connection()) as connection:
            row = connection.execute(
                """
                SELECT id FROM louveapp_schedules
                WHERE COALESCE(raw_text, '') = ?
                  AND COALESCE(page_url, '') = ?
                  AND COALESCE(date_text, '') = ?
                  AND COALESCE(time_text, '') = ?
                  AND COALESCE(person_name, '') = ?
                LIMIT 1
                """,
                (
                    schedule.raw_text,
                    schedule.page_url,
                    schedule.date_text,
                    schedule.time_text,
                    schedule.person_name,
                ),
            ).fetchone()
        return row is not None

    def _schedule_key(self, schedule: LouveAppSchedule) -> tuple[str, str, str, str, str, str]:
        return (
            schedule.category or "",
            schedule.date_text or "",
            schedule.time_text or "",
            schedule.role or "",
            schedule.person_name or "",
            schedule.raw_json or schedule.raw_text or "",
        )

    def _existing_schedule_keys(self) -> set[tuple[str, str, str, str, str, str]]:
        with closing(get_connection()) as connection:
            rows = connection.execute(
                """
                SELECT category, date_text, time_text, role, person_name, raw_json, raw_text
                FROM louveapp_schedules
                """
            ).fetchall()
        return {
            (
                row["category"] or "",
                row["date_text"] or "",
                row["time_text"] or "",
                row["role"] or "",
                row["person_name"] or "",
                row["raw_json"] or row["raw_text"] or "",
            )
            for row in rows
        }

    def save_louveapp_schedules(
        self,
        schedules: Iterable[LouveAppSchedule],
        clear_existing: bool = False,
    ) -> ImportResult:
        imported = 0
        skipped = 0
        if clear_existing:
            self.clear_louveapp_schedules()
        seen_keys = self._existing_schedule_keys()

        try:
            with closing(get_connection()) as connection, connection:
                for schedule in schedules:
                    if not schedule.imported_at:
                        schedule.imported_at = now_text()
                    key = self._schedule_key(schedule)
                    if key in seen_keys:
                        skipped += 1
                        continue
                    seen_keys.add(key)
                    data = {field: getattr(schedule, field) for field in SCHEDULE_DB_FIELDS}
                    columns = ", ".join(SCHEDULE_DB_FIELDS)
                    placeholders = ", ".join([f":{field}" for field in SCHEDULE_DB_FIELDS])
                    connection.execute(
                        f"INSERT INTO louveapp_schedules ({columns}) VALUES ({placeholders})",
                        data,
                    )
                    imported += 1
            message = f"{imported} escala(s) importada(s), {skipped} duplicata(s) ignorada(s)."
            self.insert_import_log("louveapp", "success", message)
            logger.info(message)
            return ImportResult("louveapp", "success", message, imported, skipped, [])
        except sqlite3.Error as exc:
            logger.exception("Erro ao salvar escalas do LouveApp")
            message = f"Erro ao salvar escalas no banco: {exc}"
            self.insert_import_log("louveapp", "error", message)
            return ImportResult("louveapp", "error", message, imported, skipped, [str(exc)])

    def clear_louveapp_schedules(self) -> None:
        with closing(get_connection()) as connection, connection:
            connection.execute("DELETE FROM louveapp_schedules")
        logger.info("Importacao LouveApp limpa pelo usuario")

    def list_louveapp_schedules(self, search: str = "") -> list[LouveAppSchedule]:
        params: list[object] = []
        where = ""
        if search.strip():
            query = f"%{search.strip()}%"
            where = """
                WHERE title LIKE ? OR date_text LIKE ? OR ministry LIKE ? OR role LIKE ?
                   OR person_name LIKE ? OR people_text LIKE ? OR raw_text LIKE ?
            """
            params = [query] * 7
        with closing(get_connection()) as connection:
            rows = connection.execute(
                f"SELECT * FROM louveapp_schedules {where} ORDER BY id DESC",
                params,
            ).fetchall()
        return [LouveAppSchedule.from_row(row) for row in rows]

    def list_louveapp_schedule_summaries(self) -> list[dict[str, str]]:
        with closing(get_connection()) as connection:
            summary_rows = connection.execute(
                """
                SELECT id, title, date_text, time_text, ministry, raw_json
                FROM louveapp_schedules
                WHERE category = 'api_schedule'
                ORDER BY id DESC
                """
            ).fetchall()
            song_rows = connection.execute(
                """
                SELECT raw_json
                FROM louveapp_schedules
                WHERE category = 'api_schedule_song'
                """
            ).fetchall()

        song_counts: dict[str, set[tuple[str, str, str, str]]] = {}
        for row in song_rows:
            try:
                payload = json.loads(row["raw_json"] or "{}")
            except json.JSONDecodeError:
                continue
            schedule_id = str(payload.get("schedule_id") or "")
            song = payload.get("song") if isinstance(payload.get("song"), dict) else {}
            title = str(song.get("title") or "").strip()
            artist = str(song.get("artist") or "").strip()
            key = str(song.get("key") or "").strip()
            version = str(song.get("version") or "").strip()
            if schedule_id and title:
                song_counts.setdefault(schedule_id, set()).add(
                    (title.casefold(), artist.casefold(), key.casefold(), version.casefold())
                )

        summaries: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in summary_rows:
            try:
                payload = json.loads(row["raw_json"] or "{}")
            except json.JSONDecodeError:
                payload = {}
            external_id = str(payload.get("_id") or "")
            if not external_id or external_id in seen:
                continue
            seen.add(external_id)
            song_count = len(song_counts.get(external_id, set()))
            label = f"{row['date_text']} {row['time_text']} - {row['title']} ({row['ministry']}) - {song_count} musica(s)"
            summaries.append(
                {
                    "db_id": str(row["id"]),
                    "external_id": external_id,
                    "label": label,
                    "title": row["title"] or "",
                    "date_text": row["date_text"] or "",
                    "time_text": row["time_text"] or "",
                    "ministry": row["ministry"] or "",
                    "song_count": str(song_count),
                }
            )
        return summaries

    def list_louveapp_schedule_songs(self, external_schedule_id: str) -> list[dict[str, str]]:
        if not external_schedule_id:
            return []
        with closing(get_connection()) as connection:
            rows = connection.execute(
                """
                SELECT raw_json
                FROM louveapp_schedules
                WHERE category = 'api_schedule_song'
                ORDER BY id ASC
                """
            ).fetchall()
            schedule_row = connection.execute(
                """
                SELECT raw_json
                FROM louveapp_schedules
                WHERE category = 'api_schedule'
                ORDER BY id DESC
                """
            ).fetchall()

        songs: list[dict[str, str]] = []
        seen: set[tuple[str, str, str, str]] = set()
        artist_lookup = self._artist_lookup_for_schedule(schedule_row, external_schedule_id)
        for row in rows:
            try:
                payload = json.loads(row["raw_json"] or "{}")
            except json.JSONDecodeError:
                continue
            if str(payload.get("schedule_id") or "") != external_schedule_id:
                continue
            song = payload.get("song") if isinstance(payload.get("song"), dict) else {}
            title = str(song.get("title") or "").strip()
            artist = str(song.get("artist") or "").strip()
            key = str(song.get("key") or "").strip()
            version = str(song.get("version") or "").strip()
            if not title:
                continue
            if not artist:
                artist = artist_lookup.get((title.casefold(), key.casefold(), version.casefold()), "")
                if not artist:
                    artist = artist_lookup.get((title.casefold(), "", version.casefold()), "")
                if not artist:
                    artist = artist_lookup.get((title.casefold(), key.casefold(), ""), "")
                if not artist:
                    artist = artist_lookup.get((title.casefold(), "", ""), "")
            dedupe_key = (title.casefold(), artist.casefold(), key.casefold(), version.casefold())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            display_parts = [title]
            if artist:
                display_parts.append(artist)
            if key:
                display_parts.append(f"Tom: {key}")
            display = " | ".join(display_parts)
            songs.append({"title": title, "artist": artist, "key": key, "version": version, "display": display})
        return songs

    def _artist_lookup_for_schedule(self, schedule_rows: list[sqlite3.Row], external_schedule_id: str) -> dict[tuple[str, str, str], str]:
        lookup: dict[tuple[str, str, str], str] = {}
        for row in schedule_rows:
            try:
                payload = json.loads(row["raw_json"] or "{}")
            except json.JSONDecodeError:
                continue
            if str(payload.get("_id") or "") != external_schedule_id:
                continue
            for entry in payload.get("musicasEscala") or []:
                if not isinstance(entry, dict):
                    continue
                music = entry.get("musica") if isinstance(entry.get("musica"), dict) else {}
                original = music.get("musicaOriginal") if isinstance(music.get("musicaOriginal"), dict) else {}
                artist = original.get("artista") if isinstance(original.get("artista"), dict) else {}
                title = str(original.get("nome") or music.get("nome") or "").strip()
                artist_name = str(artist.get("nome") or "").strip()
                version_id = str(entry.get("versao") or "")
                versions = music.get("versoes") if isinstance(music.get("versoes"), list) else []
                version = {}
                for candidate in versions:
                    if isinstance(candidate, dict) and str(candidate.get("_id") or "") == version_id:
                        version = candidate
                        break
                if not version and versions and isinstance(versions[0], dict):
                    version = versions[0]
                key = str(version.get("tom") or "").strip() if version else ""
                version_name = str(version.get("nomeVersao") or "").strip() if version else ""
                if title and artist_name:
                    lookup[(title.casefold(), key.casefold(), version_name.casefold())] = artist_name
                    lookup[(title.casefold(), key.casefold(), "")] = artist_name
                    lookup[(title.casefold(), "", version_name.casefold())] = artist_name
                    lookup[(title.casefold(), "", "")] = artist_name
        return lookup

    def insert_import_log(self, source: str, status: str, message: str) -> None:
        with closing(get_connection()) as connection, connection:
            connection.execute(
                "INSERT INTO import_logs(source, status, message, created_at) VALUES (?, ?, ?, ?)",
                (source, status, message, now_text()),
            )

    def list_import_logs(self, limit: int = 100) -> list[dict]:
        with closing(get_connection()) as connection:
            rows = connection.execute(
                "SELECT * FROM import_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_dashboard_stats(self) -> dict[str, object]:
        with closing(get_connection()) as connection:
            bulletins = connection.execute("SELECT COUNT(*) AS total FROM worship_bulletins").fetchone()["total"]
            people = connection.execute("SELECT COUNT(*) AS total FROM worship_people WHERE active = 1").fetchone()["total"]
            schedules = connection.execute("SELECT COUNT(*) AS total FROM louveapp_schedules").fetchone()["total"]
            last_bulletin = connection.execute(
                "SELECT date_text, dirigente, pregador FROM worship_bulletins ORDER BY id DESC LIMIT 1"
            ).fetchone()
            last_import = connection.execute(
                "SELECT source, status, message, created_at FROM import_logs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return {
            "bulletins": bulletins,
            "people": people,
            "schedules": schedules,
            "last_bulletin": dict(last_bulletin) if last_bulletin else None,
            "last_import": dict(last_import) if last_import else None,
        }

    def fetch_table_dicts(self, table_name: str) -> list[dict]:
        allowed = {"worship_bulletins", "worship_people", "louveapp_schedules", "import_logs"}
        if table_name not in allowed:
            raise ValueError("Tabela nao permitida.")
        with closing(get_connection()) as connection:
            rows = connection.execute(f"SELECT * FROM {table_name} ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]
