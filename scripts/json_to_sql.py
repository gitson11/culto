#!/usr/bin/env python3
"""Gera inserts SQL para popular a tabela `cultos` a partir de `data/cultos.json`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

COLUMN_ORDER = [
    "data_texto",
    "data_iso",
    "dirigente",
    "preludio",
    "cantor_preludio",
    "tom_preludio",
    "ref",
    "texto",
    "oracao",
    "oracao_2",
    "ofertas_ref",
    "ofertas_texto",
    "intercessao",
    "musica1",
    "cantor1",
    "tom1",
    "musica2",
    "cantor2",
    "tom2",
    "musica3",
    "cantor3",
    "tom3",
    "musica_oferta",
    "cantor_oferta",
    "tom_oferta",
    "musica_pao",
    "cantor_pao",
    "tom_pao",
    "musica_vinho",
    "cantor_vinho",
    "tom_vinho",
    "musica_extra",
    "cantor_extra",
    "tom_extra",
    "musica_final",
    "cantor_final",
    "tom_final",
    "pregador",
]

KEY_MAP = {
    "DATA": "data_texto",
    "DIRIGENTE": "dirigente",
    "PRELUDIO": "preludio",
    "CANTOR": "cantor_preludio",
    "TOM": "tom_preludio",
    "REF": "ref",
    "TEXTO": "texto",
    "ORACAO": "oracao",
    "ORACAO_2": "oracao_2",
    "OFERTAS_REF": "ofertas_ref",
    "OFERTAS_TEXTO": "ofertas_texto",
    "OFERTAS_ORACAO": "intercessao",
    "MUSICA1": "musica1",
    "CANTOR_2": "cantor1",
    "TOM_2": "tom1",
    "MUSICA2": "musica2",
    "CANTOR_3": "cantor2",
    "TOM_3": "tom2",
    "MUSICA3": "musica3",
    "CANTOR_4": "cantor3",
    "TOM_4": "tom3",
    "MUSICA": "musica_oferta",
    "CANTOR_5": "cantor_oferta",
    "TOM_5": "tom_oferta",
    "MUSICA_2": "musica_oferta",
    "MUSICA_PAO": "musica_pao",
    "CANTOR_7": "cantor_pao",
    "TOM_7": "tom_pao",
    "MUSICA_VINHO": "musica_vinho",
    "CANTOR_8": "cantor_vinho",
    "TOM_8": "tom_vinho",
    "MUSICA_EXTRA": "musica_extra",
    "CANTOR_9": "cantor_extra",
    "TOM_9": "tom_extra",
    "MUSICA_FINAL": "musica_final",
    "CANTOR_10": "cantor_final",
    "TOM_10": "tom_final",
    "PREGADOR": "pregador",
}


def sql_value(value: object | None) -> str:
    if value is None:
        return "NULL"
    text = str(value).strip()
    if not text:
        return "NULL"
    escaped = text.replace("'", "''")
    return f"'{escaped}'"


def build_row(row: dict[str, object]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    mapped["data_texto"] = sql_value(row.get("date_text"))
    mapped["data_iso"] = sql_value(row.get("date_iso"))
    raw = row.get("raw", {})
    for raw_key, column in KEY_MAP.items():
        mapped[column] = sql_value(raw.get(raw_key))
    return mapped


def iter_inserts(export: dict[str, object]) -> Iterable[str]:
    for culto in export.get("cultos", []):
        mapped = build_row(culto)
        columns = ", ".join(f"`{col}`" for col in COLUMN_ORDER)
        values = ", ".join(mapped[col] for col in COLUMN_ORDER)
        yield f"INSERT INTO `cultos` ({columns}) VALUES ({values});"


def main() -> None:
    source = Path("data/cultos.json")
    if not source.exists():
        raise SystemExit("data/cultos.json não encontrado. Rode scripts/export_cultos.py primeiro.")
    export = json.loads(source.read_text(encoding="utf-8"))
    destination = Path("data/cultos-import.sql")
    destination.write_text("\n".join(iter_inserts(export)) + "\n", encoding="utf-8")
    print(f"{destination} atualizado com {len(export.get('cultos', []))} inserts.")


if __name__ == "__main__":
    main()
