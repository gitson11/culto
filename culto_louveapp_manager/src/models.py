from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Any, Dict, Iterable, Optional


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class WorshipBulletin:
    id: Optional[int] = None
    date_text: str = ""
    dirigente: str = ""
    preludio_musica: str = ""
    preludio_cantor: str = ""
    preludio_tom: str = ""
    musica1: str = ""
    cantor1: str = ""
    tom1: str = ""
    ref1: str = ""
    texto1: str = ""
    musica2: str = ""
    cantor2: str = ""
    tom2: str = ""
    ref2: str = ""
    texto2: str = ""
    musica3: str = ""
    cantor3: str = ""
    tom3: str = ""
    ref3: str = ""
    texto3: str = ""
    oracao_louvor: str = ""
    ref_louvor: str = ""
    texto_louvor: str = ""
    ofertas_ref: str = ""
    ofertas_texto: str = ""
    ofertas_oracao: str = ""
    musica4: str = ""
    cantor4: str = ""
    tom4: str = ""
    musica5: str = ""
    cantor5: str = ""
    tom5: str = ""
    oracao_intercessao: str = ""
    pregador: str = ""
    musica_pao: str = ""
    cantor_pao: str = ""
    tom_pao: str = ""
    musica_vinho: str = ""
    cantor_vinho: str = ""
    tom_vinho: str = ""
    musica_extra: str = ""
    cantor_extra: str = ""
    tom_extra: str = ""
    musica_final: str = ""
    cantor_final: str = ""
    tom_final: str = ""
    source: str = "manual"
    raw_json: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_db_dict(self, include_id: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        if not include_id:
            data.pop("id", None)
        return data

    @classmethod
    def from_row(cls, row: Any) -> "WorshipBulletin":
        return _dataclass_from_row(cls, row)


@dataclass
class WorshipSong:
    title: str = ""
    singer: str = ""
    key: str = ""
    section: str = ""


@dataclass
class WorshipPerson:
    id: Optional[int] = None
    name: str = ""
    active: int = 1
    created_at: str = ""

    @classmethod
    def from_row(cls, row: Any) -> "WorshipPerson":
        return _dataclass_from_row(cls, row)


@dataclass
class LouveAppSchedule:
    id: Optional[int] = None
    category: str = ""
    title: str = ""
    date_text: str = ""
    time_text: str = ""
    ministry: str = ""
    role: str = ""
    person_name: str = ""
    people_text: str = ""
    raw_text: str = ""
    page_url: str = ""
    raw_json: str = ""
    imported_at: str = ""

    @classmethod
    def from_row(cls, row: Any) -> "LouveAppSchedule":
        return _dataclass_from_row(cls, row)


@dataclass
class ImportResult:
    source: str
    status: str
    message: str
    imported_count: int = 0
    skipped_count: int = 0
    errors: list[str] | None = None


def _dataclass_from_row(model_cls: type, row: Any):
    row_keys = set(row.keys()) if hasattr(row, "keys") else set(row)
    values = {field.name: row[field.name] for field in fields(model_cls) if field.name in row_keys}
    return model_cls(**values)


BULLETIN_FIELDS = [field.name for field in fields(WorshipBulletin)]
BULLETIN_DB_FIELDS = [name for name in BULLETIN_FIELDS if name != "id"]
SCHEDULE_FIELDS = [field.name for field in fields(LouveAppSchedule)]
SCHEDULE_DB_FIELDS = [name for name in SCHEDULE_FIELDS if name != "id"]
PERSON_FIELDS = [field.name for field in fields(WorshipPerson)]


def dataclasses_to_dicts(items: Iterable[Any]) -> list[dict[str, Any]]:
    return [asdict(item) for item in items]
