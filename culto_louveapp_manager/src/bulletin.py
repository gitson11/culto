from __future__ import annotations

from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from src.config import OUTPUT_DIR
from src.database import Database
from src.logger import get_logger
from src.models import WorshipBulletin


logger = get_logger(__name__)


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value or "sem_data").strip("_")
    return cleaned or "sem_data"


def _add_heading(document: Document, text: str, level: int = 1) -> None:
    paragraph = document.add_heading(text, level=level)
    for run in paragraph.runs:
        run.font.name = "Arial"


def _add_labeled_line(document: Document, label: str, value: str) -> None:
    if not value:
        return
    paragraph = document.add_paragraph()
    paragraph_format = paragraph.paragraph_format
    paragraph_format.space_after = Pt(4)
    label_run = paragraph.add_run(f"{label}: ")
    label_run.bold = True
    paragraph.add_run(value)


def _has_any(bulletin: WorshipBulletin, fields: list[str]) -> bool:
    return any((getattr(bulletin, field) or "").strip() for field in fields)


def _build_document(bulletin: WorshipBulletin) -> Document:
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(10.5)

    title = document.add_heading("BOLETIM DE CULTO", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_labeled_line(document, "Data", bulletin.date_text)
    _add_labeled_line(document, "Dirigente", bulletin.dirigente)
    _add_labeled_line(document, "Pregador", bulletin.pregador)

    _add_heading(document, "PRELUDIO", 1)
    _add_labeled_line(document, "Musica", bulletin.preludio_musica)
    _add_labeled_line(document, "Cantor", bulletin.preludio_cantor)
    _add_labeled_line(document, "Tom", bulletin.preludio_tom)

    _add_heading(document, "LOUVOR CONGREGACIONAL", 1)
    for number in (1, 2, 3):
        _add_heading(document, f"Musica {number}", 2)
        _add_labeled_line(document, "Musica", getattr(bulletin, f"musica{number}"))
        _add_labeled_line(document, "Cantor", getattr(bulletin, f"cantor{number}"))
        _add_labeled_line(document, "Tom", getattr(bulletin, f"tom{number}"))
        _add_labeled_line(document, "Referencia biblica", getattr(bulletin, f"ref{number}"))
        _add_labeled_line(document, "Texto", getattr(bulletin, f"texto{number}"))

    _add_heading(document, "ORACAO", 1)
    _add_labeled_line(document, "Oracao", bulletin.oracao_louvor)
    _add_labeled_line(document, "Referencia", bulletin.ref_louvor)
    _add_labeled_line(document, "Texto", bulletin.texto_louvor)

    _add_heading(document, "OFERTAS", 1)
    _add_labeled_line(document, "Referencia", bulletin.ofertas_ref)
    _add_labeled_line(document, "Texto", bulletin.ofertas_texto)
    _add_labeled_line(document, "Oracao", bulletin.ofertas_oracao)

    _add_heading(document, "MUSICAS FINAIS", 1)
    for number in (4, 5):
        _add_heading(document, f"Musica {number}", 2)
        _add_labeled_line(document, "Musica", getattr(bulletin, f"musica{number}"))
        _add_labeled_line(document, "Cantor", getattr(bulletin, f"cantor{number}"))
        _add_labeled_line(document, "Tom", getattr(bulletin, f"tom{number}"))

    if _has_any(
        bulletin,
        [
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
        ],
    ):
        _add_heading(document, "SANTA CEIA", 1)
        for label, prefix in (
            ("Musica Pao", "pao"),
            ("Musica Vinho", "vinho"),
            ("Musica Extra", "extra"),
            ("Musica Final", "final"),
        ):
            _add_heading(document, label, 2)
            field = "musica_pao" if prefix == "pao" else f"musica_{prefix}"
            singer = "cantor_pao" if prefix == "pao" else f"cantor_{prefix}"
            key = "tom_pao" if prefix == "pao" else f"tom_{prefix}"
            _add_labeled_line(document, "Musica", getattr(bulletin, field))
            _add_labeled_line(document, "Cantor", getattr(bulletin, singer))
            _add_labeled_line(document, "Tom", getattr(bulletin, key))

    return document


def generate_bulletin_docx(bulletin_id: int, output_path: str | Path | None = None) -> Path:
    database = Database()
    bulletin = database.get_bulletin(bulletin_id)
    if not bulletin:
        raise ValueError(f"Boletim id={bulletin_id} nao encontrado.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(output_path) if output_path else OUTPUT_DIR / f"boletim_{_safe_filename(bulletin.date_text)}_{bulletin_id}.docx"
    document = _build_document(bulletin)
    document.save(path)
    logger.info("Boletim DOCX gerado: %s", path)
    return path


def generate_bulletin_by_date(date_text: str, output_path: str | Path | None = None) -> Path:
    database = Database()
    bulletin = database.get_bulletin_by_date(date_text)
    if not bulletin or bulletin.id is None:
        raise ValueError(f"Nenhum boletim encontrado para a data: {date_text}")
    return generate_bulletin_docx(bulletin.id, output_path)
