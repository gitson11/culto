from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from src.config import get_headless, get_slow_mo_ms, validate_louveapp_credentials
from src.database import Database
from src.logger import get_logger
from src.louveapp_browser import (
    ProgressCallback,
    fetch_remaining_schedule_pages,
    save_debug_artifacts,
)
from src.louveapp_robust_session import LouveAppRobustBrowserSession
from src.louveapp_scraper import parse_louveapp_api_schedule_records, scrape_louveapp_schedules
from src.models import ImportResult
from src.parser import dedupe_schedules


logger = get_logger(__name__)


def _progress(callback: ProgressCallback, message: str) -> None:
    if callback:
        callback(message)


def _looks_relevant_api_url(url: str) -> bool:
    lowered = url.lower()
    if "api.louveapp.com.br" not in lowered:
        return False
    relevant_terms = (
        "schedule",
        "schedules",
        "escala",
        "escalas",
        "culto",
        "cultos",
        "repertorio",
        "repertórios",
        "repertorios",
        "musica",
        "musicas",
        "música",
        "músicas",
        "ministerio",
        "ministerios",
    )
    return any(term in lowered for term in relevant_terms)


def _body_mentions_scale_or_music(body: str) -> bool:
    lowered = (body or "").lower()
    relevant_terms = (
        "musicasescala",
        "musica",
        "musicas",
        "música",
        "músicas",
        "usuarios",
        "instrumentos",
        "ministerio",
        "descricao",
        "escala",
        "culto",
    )
    return any(term in lowered for term in relevant_terms)


def _attach_broad_api_capture(page, records: list[dict]) -> None:
    def handler(response) -> None:
        try:
            url = response.url
            if not _looks_relevant_api_url(url):
                return
            if response.status >= 400:
                return
            content_type = response.headers.get("content-type", "").lower()
            if "json" not in content_type:
                return
            body = response.text()
            if not _body_mentions_scale_or_music(body):
                return
            parsed = urlparse(url)
            safe_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{parsed.query}"
            records.append(
                {
                    "url": safe_url,
                    "status": response.status,
                    "body": body,
                    "request_headers": {
                        key: value
                        for key, value in response.request.headers.items()
                        if key.lower() not in {"accept-encoding", "connection", "content-length", "host"}
                    },
                }
            )
        except Exception:
            logger.exception("Falha ao capturar resposta ampla da API LouveApp")

    page.on("response", handler)


def import_louveapp_schedules(progress: ProgressCallback = None, clear_existing: bool = False) -> ImportResult:
    logger.info("Inicio da importacao LouveApp com navegacao ativa")
    database = Database()
    email, password = validate_louveapp_credentials()
    session = LouveAppRobustBrowserSession(email, password, get_headless(), get_slow_mo_ms())
    api_records: list[dict] = []
    try:
        page = session.start()
        _attach_broad_api_capture(page, api_records)
        session.login(progress)

        _progress(progress, "Abrindo telas de escalas, cultos e repertorios no LouveApp...")
        visual_schedules = scrape_louveapp_schedules(page, progress)

        _progress(progress, "Aguardando carregamento das musicas e escalas da API...")
        page.wait_for_timeout(3_000)
        fetch_remaining_schedule_pages(page, api_records, progress)
        api_schedules = parse_louveapp_api_schedule_records(api_records)
        schedules = dedupe_schedules([*visual_schedules, *api_schedules])

        if api_schedules:
            _progress(progress, f"{len(api_schedules)} registro(s) lido(s) pela API LouveApp.")
        if visual_schedules:
            _progress(progress, f"{len(visual_schedules)} registro(s) lido(s) visualmente no LouveApp.")

        if not schedules:
            artifacts = save_debug_artifacts(page, "louveapp_no_schedules_or_songs_found")
            message = (
                "Nenhuma escala ou musica foi encontrada. O app abriu o LouveApp, mas nao conseguiu reconhecer "
                "as telas/API atuais. Arquivos de debug foram salvos em data/debug."
            )
            if artifacts:
                message += f" HTML: {Path(artifacts.get('html', '')).name}"
            database.insert_import_log("louveapp", "warning", message)
            return ImportResult("louveapp", "warning", message, 0, 0, [])

        result = database.save_louveapp_schedules(schedules, clear_existing=clear_existing)
        logger.info("Fim da importacao LouveApp: %s", result.message)
        return result
    except Exception as exc:
        logger.exception("Falha na importacao LouveApp com navegacao ativa")
        message = str(exc)
        database.insert_import_log("louveapp", "error", message)
        return ImportResult("louveapp", "error", message, 0, 0, [message])
    finally:
        session.close()
