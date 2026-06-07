#!/usr/bin/env python3
"""Gera PDFs dos boletins usando o template HTML + WeasyPrint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

DATA_FILE = Path("data/cultos.json")
TEMPLATE_DIR = Path("backend/templates")
OUTPUT_DIR = Path("out/boletins")
MUSIC_FIELDS = [
    ("Louvor 1", "musica1", "cantor1", "tom1"),
    ("Louvor 2", "musica2", "cantor2", "tom2"),
    ("Louvor 3", "musica3", "cantor3", "tom3"),
    ("Oferta / Intercessão", "musica_oferta", "cantor_oferta", "tom_oferta"),
    ("Pão", "musica_pao", "cantor_pao", "tom_pao"),
    ("Vinho", "musica_vinho", "cantor_vinho", "tom_vinho"),
    ("Extra", "musica_extra", "cantor_extra", "tom_extra"),
    ("Final", "musica_final", "cantor_final", "tom_final"),
]


def build_music_html(row: Dict[str, Any]) -> str:
    lines: list[str] = []
    for label, song, singer, tone in MUSIC_FIELDS:
        title = row.get(song)
        if not title:
            continue
        parts = [f"<strong>{label}:</strong> {title}"]
        singer_value = row.get(singer)
        if singer_value:
            parts.append(f"Cantor: {singer_value}")
        tone_value = row.get(tone)
        if tone_value:
            parts.append(f"Tom: {tone_value}")
        lines.append(f"<li>{' · '.join(parts)}</li>")
    return "\n".join(lines) if lines else "<li>Sem músicas registradas.</li>"


def normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {key: raw.get(key) for key in raw.keys()}
    normalized["musicas"] = build_music_html(normalized)
    normalized["oracao"] = normalized.get("oracao") or normalized.get("oracao_1")
    return normalized


def safe_filename(text: str) -> str:
    sanitized = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text.strip())
    return sanitized or "boletim"


def main() -> None:
    if not DATA_FILE.exists():
        raise SystemExit("Execute python scripts/export_cultos.py antes de gerar PDFs.")
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("boletim-template.html")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for culto in data.get("cultos", []):
        context = normalize_record(culto)
        filename = safe_filename(culto.get("date_iso") or culto.get("date_text") or "boletim")
        html = template.render(**context)
        pdf_path = OUTPUT_DIR / f"{filename}.pdf"
        HTML(string=html).write_pdf(str(pdf_path))
        print("Gerado", pdf_path)


if __name__ == "__main__":
    main()
