"""Importação do arquivo Excel legado (BOLETIM_VBA_CORRIGIDO.xlsm).

Lê dados das abas Planilha1/CULTOS e LOUVOR/INTEGRANTES.
Nunca executa macros VBA — apenas leitura de dados.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from openpyxl import load_workbook

from src.config import LEGACY_DIR, get_legacy_xlsm_path
from src.database import insert_bulletin, insert_person, log_import
from src.logger import get_logger
from src.models import ImportResult, WorshipBulletin

logger = get_logger()

# Mapeamento de colunas A:AT (índice 0-based) para campos do WorshipBulletin
_COLUMN_MAP: list[tuple[int, str]] = [
    (0, "date_text"),
    (1, "dirigente"),
    (2, "preludio_musica"),
    (3, "preludio_cantor"),
    (4, "preludio_tom"),
    (5, "ref1"),
    (6, "texto1"),
    (7, "musica1"),
    (8, "cantor1"),
    (9, "tom1"),
    (10, "ref2"),
    (11, "texto2"),
    (12, "musica2"),
    (13, "cantor2"),
    (14, "tom2"),
    (15, "ref3"),
    (16, "texto3"),
    (17, "musica3"),
    (18, "cantor3"),
    (19, "tom3"),
    (20, "oracao_louvor"),
    (21, "ref_louvor"),
    (22, "texto_louvor"),
    (23, "ofertas_ref"),
    (24, "ofertas_texto"),
    (25, "ofertas_oracao"),
    (26, "musica4"),
    (27, "cantor4"),
    (28, "tom4"),
    (29, "musica5"),
    (30, "cantor5"),
    (31, "tom5"),
    (32, "oracao_intercessao"),
    (33, "pregador"),
    (34, "musica_pao"),
    (35, "cantor_pao"),
    (36, "tom_pao"),
    (37, "musica_vinho"),
    (38, "cantor_vinho"),
    (39, "tom_vinho"),
    (40, "musica_extra"),
    (41, "cantor_extra"),
    (42, "tom_extra"),
    (43, "musica_final"),
    (44, "cantor_final"),
    (45, "tom_final"),
]


def _safe_str(value: Any) -> str:
    """Converte valor de célula para string, preservando quebras de linha."""
    if value is None:
        return ""
    s = str(value).strip()
    # Normaliza marcadores de quebra de linha do Excel
    s = s.replace("_x000D_\n", "\n").replace("_x000D_", "\n")
    return s


def find_legacy_file() -> Optional[Path]:
    """Procura o arquivo XLSM legado na pasta legacy/."""
    return get_legacy_xlsm_path()


def inspect_legacy_workbook(path: Path) -> dict[str, Any]:
    """Inspeciona o workbook e retorna informações sobre abas e cabeçalhos."""
    logger.info("Inspecionando arquivo legado: %s", path.name)
    wb = load_workbook(str(path), data_only=True, read_only=True)

    info: dict[str, Any] = {
        "file_name": path.name,
        "file_size_kb": path.stat().st_size // 1024,
        "sheet_names": wb.sheetnames,
        "data_sheet": None,
        "people_sheet": None,
        "data_headers": [],
        "data_row_count": 0,
        "people_count": 0,
    }

    # Encontra aba de dados
    for name in ("Planilha1", "CULTOS", "Planilha 1"):
        if name in wb.sheetnames:
            info["data_sheet"] = name
            break
    if not info["data_sheet"] and wb.sheetnames:
        # Tenta a primeira aba que tenha "DATA" como cabeçalho
        for name in wb.sheetnames:
            ws = wb[name]
            first_row = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            if "DATA" in [str(v).upper().strip() for v in first_row if v]:
                info["data_sheet"] = name
                break

    # Lê cabeçalhos da aba de dados
    if info["data_sheet"]:
        ws = wb[info["data_sheet"]]
        headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
        info["data_headers"] = [str(h) if h else "" for h in headers]
        # Conta linhas com data
        count = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row and row[0]:
                count += 1
        info["data_row_count"] = count

    # Encontra aba de pessoas
    for name in ("LOUVOR", "INTEGRANTES", "Louvor", "Integrantes"):
        if name in wb.sheetnames:
            info["people_sheet"] = name
            break

    if info["people_sheet"]:
        ws = wb[info["people_sheet"]]
        count = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row and row[0] and str(row[0]).strip():
                count += 1
        info["people_count"] = count

    wb.close()
    logger.info(
        "Inspeção concluída: abas=%s, dados=%d linhas, pessoas=%d",
        info["sheet_names"], info["data_row_count"], info["people_count"],
    )
    return info


def import_legacy_bulletins(path: Path) -> ImportResult:
    """Importa boletins da aba de dados do XLSM."""
    result = ImportResult(source="legacy_xlsm")

    try:
        info = inspect_legacy_workbook(path)
        if not info["data_sheet"]:
            result.status = "error"
            result.message = "Nenhuma aba de dados encontrada (Planilha1, CULTOS)."
            log_import(result.source, result.status, result.message)
            return result

        wb = load_workbook(str(path), data_only=True, read_only=True)
        ws = wb[info["data_sheet"]]

        imported = 0
        errors = []

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not row[0]:
                continue  # Ignora linhas sem DATA

            try:
                bulletin = WorshipBulletin(source="legacy_xlsm")

                # Mapeia colunas para campos
                for col_idx, field_name in _COLUMN_MAP:
                    value = ""
                    if col_idx < len(row):
                        value = _safe_str(row[col_idx])
                    setattr(bulletin, field_name, value)

                # Salva JSON bruto para referência
                raw = {}
                for col_idx, field_name in _COLUMN_MAP:
                    if col_idx < len(row):
                        raw[field_name] = _safe_str(row[col_idx])
                bulletin.raw_json = json.dumps(raw, ensure_ascii=False)

                insert_bulletin(bulletin)
                imported += 1

            except Exception as exc:
                err_msg = f"Linha {row_idx}: {exc}"
                errors.append(err_msg)
                logger.warning("Erro ao importar linha %d: %s", row_idx, exc)

        wb.close()

        result.records_count = imported
        result.errors = errors
        result.message = f"{imported} boletins importados com sucesso."
        if errors:
            result.message += f" {len(errors)} erros."
        log_import(result.source, result.status, result.message)
        logger.info("Importação de boletins legados concluída: %d importados", imported)

    except Exception as exc:
        result.status = "error"
        result.message = f"Erro ao importar boletins: {exc}"
        result.errors.append(str(exc))
        log_import(result.source, result.status, result.message)
        logger.error("Falha na importação legada: %s", exc)

    return result


def import_legacy_people(path: Path) -> ImportResult:
    """Importa pessoas do louvor da aba LOUVOR/INTEGRANTES."""
    result = ImportResult(source="legacy_people")

    try:
        wb = load_workbook(str(path), data_only=True, read_only=True)

        # Encontra a aba
        people_sheet = None
        for name in ("LOUVOR", "INTEGRANTES", "Louvor", "Integrantes"):
            if name in wb.sheetnames:
                people_sheet = name
                break

        if not people_sheet:
            result.status = "error"
            result.message = "Nenhuma aba de pessoas encontrada (LOUVOR, INTEGRANTES)."
            wb.close()
            log_import(result.source, result.status, result.message)
            return result

        ws = wb[people_sheet]
        imported = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            name = str(row[0]).strip()
            if name and name.upper() != "NOME":
                insert_person(name)
                imported += 1

        wb.close()

        result.records_count = imported
        result.message = f"{imported} pessoas importadas."
        log_import(result.source, result.status, result.message)
        logger.info("Importação de pessoas legadas concluída: %d", imported)

    except Exception as exc:
        result.status = "error"
        result.message = f"Erro ao importar pessoas: {exc}"
        result.errors.append(str(exc))
        log_import(result.source, result.status, result.message)
        logger.error("Falha na importação de pessoas: %s", exc)

    return result


def try_extract_vba_summary(path: Path) -> str:
    """Tenta extrair resumo das macros VBA (sem executá-las)."""
    summary_lines = ["=== Resumo VBA ===", f"Arquivo: {path.name}", ""]

    try:
        import oletools.olevba as olevba

        vba_parser = olevba.VBA_Parser(str(path))
        if vba_parser.detect_vba_macros():
            summary_lines.append("Macros VBA detectadas:")
            for vba_filename, stream_path, vba_code_type, vba_code in vba_parser.extract_macros():
                summary_lines.append(f"  - {vba_filename} ({vba_code_type})")
                # Extrai nomes de Sub/Function
                for line in vba_code.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith(("Sub ", "Function ", "Private Sub ", "Private Function ")):
                        summary_lines.append(f"    → {stripped.split('(')[0]}")
        else:
            summary_lines.append("Nenhuma macro VBA encontrada.")
        vba_parser.close()
    except ImportError:
        summary_lines.append("oletools não instalado. Instale com: pip install oletools")
    except Exception as exc:
        summary_lines.append(f"Erro ao ler VBA: {exc}")

    return "\n".join(summary_lines)
