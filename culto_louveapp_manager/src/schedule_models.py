from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Dict, Optional


@dataclass
class ScaleModel:
    id: Optional[int] = None
    name: str = ""
    service_type: str = ""
    description: str = ""
    active: int = 1
    created_at: str = ""
    updated_at: str = ""

    def to_db_dict(self, include_id: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        if not include_id:
            data.pop("id", None)
        return data

    @classmethod
    def from_row(cls, row: Any) -> "ScaleModel":
        row_keys = set(row.keys()) if hasattr(row, "keys") else set(row)
        values = {field.name: row[field.name] for field in fields(cls) if field.name in row_keys}
        return cls(**values)


@dataclass
class ScaleModelSlot:
    id: Optional[int] = None
    model_id: Optional[int] = None
    function_name: str = ""
    quantity: int = 1
    desired_instruments: str = ""
    desired_voice: str = ""
    notes: str = ""
    sort_order: int = 0
    created_at: str = ""
    updated_at: str = ""

    def to_db_dict(self, include_id: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        if not include_id:
            data.pop("id", None)
        return data

    @classmethod
    def from_row(cls, row: Any) -> "ScaleModelSlot":
        row_keys = set(row.keys()) if hasattr(row, "keys") else set(row)
        values = {field.name: row[field.name] for field in fields(cls) if field.name in row_keys}
        return cls(**values)


SCALE_MODEL_FIELDS = [field.name for field in fields(ScaleModel)]
SCALE_MODEL_DB_FIELDS = [name for name in SCALE_MODEL_FIELDS if name != "id"]
SCALE_MODEL_SLOT_FIELDS = [field.name for field in fields(ScaleModelSlot)]
SCALE_MODEL_SLOT_DB_FIELDS = [name for name in SCALE_MODEL_SLOT_FIELDS if name != "id"]
