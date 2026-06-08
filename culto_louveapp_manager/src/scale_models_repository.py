from __future__ import annotations

from contextlib import closing
import sqlite3
from typing import Optional

from src.database import get_connection
from src.models import now_text
from src.scale_models import (
    SCALE_MODEL_DB_FIELDS,
    SCALE_MODEL_SLOT_DB_FIELDS,
    ScaleModel,
    ScaleModelSlot,
)


class ScaleModelRepository:
    def ensure_tables(self) -> None:
        with closing(get_connection()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scale_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    service_type TEXT,
                    description TEXT,
                    active INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scale_model_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id INTEGER NOT NULL,
                    function_name TEXT,
                    quantity INTEGER DEFAULT 1,
                    desired_instruments TEXT,
                    desired_voice TEXT,
                    notes TEXT,
                    sort_order INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY(model_id) REFERENCES scale_models(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_scale_models_name ON scale_models(name)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_scale_model_slots_model ON scale_model_slots(model_id)")

    def save_model(self, model: ScaleModel) -> int:
        self.ensure_tables()
        model.name = " ".join((model.name or "").strip().split())
        if not model.name:
            raise ValueError("Informe o nome do modelo de escala.")
        now = now_text()
        if not model.created_at:
            model.created_at = now
        model.updated_at = now
        data = model.to_db_dict()
        columns = ", ".join(SCALE_MODEL_DB_FIELDS)
        placeholders = ", ".join([f":{field}" for field in SCALE_MODEL_DB_FIELDS])
        updates = ", ".join([f"{field} = excluded.{field}" for field in SCALE_MODEL_DB_FIELDS if field != "created_at"])
        with closing(get_connection()) as connection, connection:
            connection.execute(
                f"INSERT INTO scale_models ({columns}) VALUES ({placeholders}) ON CONFLICT(name) DO UPDATE SET {updates}",
                data,
            )
            row = connection.execute("SELECT id FROM scale_models WHERE name = ?", (model.name,)).fetchone()
        return int(row["id"])

    def update_model(self, model_id: int, model: ScaleModel) -> None:
        self.ensure_tables()
        model.name = " ".join((model.name or "").strip().split())
        if not model.name:
            raise ValueError("Informe o nome do modelo de escala.")
        model.updated_at = now_text()
        data = model.to_db_dict()
        data["id"] = model_id
        assignments = ", ".join([f"{field} = :{field}" for field in SCALE_MODEL_DB_FIELDS if field != "created_at"])
        with closing(get_connection()) as connection, connection:
            connection.execute(f"UPDATE scale_models SET {assignments} WHERE id = :id", data)

    def delete_model(self, model_id: int) -> None:
        self.ensure_tables()
        with closing(get_connection()) as connection, connection:
            connection.execute("DELETE FROM scale_model_slots WHERE model_id = ?", (model_id,))
            connection.execute("DELETE FROM scale_models WHERE id = ?", (model_id,))

    def get_model(self, model_id: int) -> Optional[ScaleModel]:
        self.ensure_tables()
        with closing(get_connection()) as connection:
            row = connection.execute("SELECT * FROM scale_models WHERE id = ?", (model_id,)).fetchone()
        return ScaleModel.from_row(row) if row else None

    def list_models(self, search: str = "") -> list[ScaleModel]:
        self.ensure_tables()
        params: list[object] = []
        where = ""
        if search.strip():
            query = f"%{search.strip()}%"
            where = "WHERE name LIKE ? OR service_type LIKE ? OR description LIKE ?"
            params = [query, query, query]
        with closing(get_connection()) as connection:
            rows = connection.execute(
                f"SELECT * FROM scale_models {where} ORDER BY active DESC, name COLLATE NOCASE",
                params,
            ).fetchall()
        return [ScaleModel.from_row(row) for row in rows]

    def save_slot(self, slot: ScaleModelSlot) -> int:
        self.ensure_tables()
        if not slot.model_id:
            raise ValueError("Selecione um modelo de escala.")
        slot.function_name = " ".join((slot.function_name or "").strip().split())
        if not slot.function_name:
            raise ValueError("Informe a funcao da escala.")
        slot.quantity = max(1, int(slot.quantity or 1))
        now = now_text()
        if not slot.created_at:
            slot.created_at = now
        slot.updated_at = now
        data = slot.to_db_dict()
        columns = ", ".join(SCALE_MODEL_SLOT_DB_FIELDS)
        placeholders = ", ".join([f":{field}" for field in SCALE_MODEL_SLOT_DB_FIELDS])
        with closing(get_connection()) as connection, connection:
            cursor = connection.execute(f"INSERT INTO scale_model_slots ({columns}) VALUES ({placeholders})", data)
            return int(cursor.lastrowid)

    def update_slot(self, slot_id: int, slot: ScaleModelSlot) -> None:
        self.ensure_tables()
        slot.quantity = max(1, int(slot.quantity or 1))
        slot.updated_at = now_text()
        data = slot.to_db_dict()
        data["id"] = slot_id
        assignments = ", ".join([f"{field} = :{field}" for field in SCALE_MODEL_SLOT_DB_FIELDS if field != "created_at"])
        with closing(get_connection()) as connection, connection:
            connection.execute(f"UPDATE scale_model_slots SET {assignments} WHERE id = :id", data)

    def delete_slot(self, slot_id: int) -> None:
        self.ensure_tables()
        with closing(get_connection()) as connection, connection:
            connection.execute("DELETE FROM scale_model_slots WHERE id = ?", (slot_id,))

    def get_slot(self, slot_id: int) -> Optional[ScaleModelSlot]:
        self.ensure_tables()
        with closing(get_connection()) as connection:
            row = connection.execute("SELECT * FROM scale_model_slots WHERE id = ?", (slot_id,)).fetchone()
        return ScaleModelSlot.from_row(row) if row else None

    def list_slots(self, model_id: int) -> list[ScaleModelSlot]:
        self.ensure_tables()
        with closing(get_connection()) as connection:
            rows = connection.execute(
                "SELECT * FROM scale_model_slots WHERE model_id = ? ORDER BY sort_order, id",
                (model_id,),
            ).fetchall()
        return [ScaleModelSlot.from_row(row) for row in rows]
