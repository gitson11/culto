from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from typing import Optional

from src.database import get_connection
from src.models import now_text
from src.scale_generator import GeneratedScaleAssignment, GeneratedScaleResult


@dataclass
class SavedScale:
    id: int
    title: str
    service_date: str
    model_name: str
    status: str
    created_at: str


class GeneratedScalesRepository:
    def ensure_tables(self) -> None:
        with closing(get_connection()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS generated_scales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    service_date TEXT,
                    model_id INTEGER,
                    model_name TEXT,
                    status TEXT DEFAULT 'rascunho',
                    notes TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS generated_scale_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scale_id INTEGER NOT NULL,
                    function_name TEXT,
                    person_name TEXT,
                    reason TEXT,
                    warning TEXT,
                    sort_order INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY(scale_id) REFERENCES generated_scales(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_generated_scales_date ON generated_scales(service_date)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_generated_assignments_scale ON generated_scale_assignments(scale_id)")

    def save_generated_scale(self, result: GeneratedScaleResult, service_date: str = "", notes: str = "") -> int:
        self.ensure_tables()
        current_time = now_text()
        title = f"{result.model.name} - {service_date}" if service_date else result.model.name
        with closing(get_connection()) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO generated_scales(title, service_date, model_id, model_name, status, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (title, service_date, result.model.id, result.model.name, "rascunho", notes, current_time, current_time),
            )
            scale_id = int(cursor.lastrowid)
            for index, assignment in enumerate(result.assignments, start=1):
                connection.execute(
                    """
                    INSERT INTO generated_scale_assignments(
                        scale_id, function_name, person_name, reason, warning, sort_order, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        scale_id,
                        assignment.function_name,
                        assignment.person_name,
                        assignment.reason,
                        assignment.warning,
                        index,
                        current_time,
                        current_time,
                    ),
                )
        return scale_id

    def list_scales(self) -> list[SavedScale]:
        self.ensure_tables()
        with closing(get_connection()) as connection:
            rows = connection.execute(
                """
                SELECT id, title, service_date, model_name, status, created_at
                FROM generated_scales
                ORDER BY id DESC
                """
            ).fetchall()
        return [
            SavedScale(
                id=int(row["id"]),
                title=row["title"] or "",
                service_date=row["service_date"] or "",
                model_name=row["model_name"] or "",
                status=row["status"] or "",
                created_at=row["created_at"] or "",
            )
            for row in rows
        ]

    def get_assignments(self, scale_id: int) -> list[GeneratedScaleAssignment]:
        self.ensure_tables()
        with closing(get_connection()) as connection:
            rows = connection.execute(
                """
                SELECT function_name, person_name, reason, warning
                FROM generated_scale_assignments
                WHERE scale_id = ?
                ORDER BY sort_order, id
                """,
                (scale_id,),
            ).fetchall()
        return [
            GeneratedScaleAssignment(
                function_name=row["function_name"] or "",
                person_name=row["person_name"] or "",
                reason=row["reason"] or "",
                warning=row["warning"] or "",
            )
            for row in rows
        ]

    def get_scale(self, scale_id: int) -> Optional[SavedScale]:
        self.ensure_tables()
        with closing(get_connection()) as connection:
            row = connection.execute(
                "SELECT id, title, service_date, model_name, status, created_at FROM generated_scales WHERE id = ?",
                (scale_id,),
            ).fetchone()
        if not row:
            return None
        return SavedScale(
            id=int(row["id"]),
            title=row["title"] or "",
            service_date=row["service_date"] or "",
            model_name=row["model_name"] or "",
            status=row["status"] or "",
            created_at=row["created_at"] or "",
        )

    def delete_scale(self, scale_id: int) -> None:
        self.ensure_tables()
        with closing(get_connection()) as connection, connection:
            connection.execute("DELETE FROM generated_scale_assignments WHERE scale_id = ?", (scale_id,))
            connection.execute("DELETE FROM generated_scales WHERE id = ?", (scale_id,))

    def build_whatsapp_text(self, scale_id: int) -> str:
        scale = self.get_scale(scale_id)
        if not scale:
            raise ValueError("Escala nao encontrada.")
        assignments = self.get_assignments(scale_id)
        header = scale.title or f"Escala - {scale.model_name}"
        lines = [f"*{header.upper()}*", ""]
        if scale.service_date:
            lines.append(f"*Data/periodo:* {scale.service_date}")
        if scale.model_name:
            lines.append(f"*Modelo:* {scale.model_name}")
        lines.append("")
        lines.append("*Equipe escalada:*")
        for assignment in assignments:
            person = assignment.person_name or "A definir"
            lines.append(f"- *{assignment.function_name}:* {person}")
        warnings = [assignment for assignment in assignments if assignment.warning]
        if warnings:
            lines.append("")
            lines.append("*Avisos para revisao:*")
            for assignment in warnings:
                lines.append(f"- {assignment.function_name}: {assignment.warning}")
        lines.append("")
        lines.append("_Revise a escala antes de publicar._")
        return "\n".join(lines)
