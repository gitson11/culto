from __future__ import annotations

from datetime import datetime
import json
from typing import Callable, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.logger import get_logger
from src.models import LouveAppSchedule, now_text
from src.parser import dedupe_schedules, parse_body_fallback, parse_schedule_text


logger = get_logger(__name__)


ProgressCallback = Optional[Callable[[str], None]]

MENU_TEXTS = [
    "Escala",
    "Escalas",
    "Agenda",
    "Culto",
    "Cultos",
    "Louvor",
    "Ministério",
    "Ministérios",
    "Ministerio",
    "Ministerios",
    "Eventos",
    "Programação",
    "Programacao",
    "Voluntários",
    "Voluntarios",
    "Serviços",
    "Servicos",
]

ROUTES = [
    "#/escala",
    "#/escalas",
    "#/agenda",
    "#/cultos",
    "#/eventos",
    "#/ministerios",
    "#/ministerios/escala",
    "#/voluntarios",
    "#/servicos",
]

CONTENT_SELECTORS = [
    "table tbody tr",
    "mat-row",
    ".mat-row",
    ".mat-table .mat-row",
    ".card",
    ".mat-card",
    "mat-card",
    ".list-group-item",
    "li",
    '[class*="escala" i]',
    '[class*="schedule" i]',
    '[class*="culto" i]',
    '[class*="evento" i]',
    '[class*="ministry" i]',
    '[class*="ministerio" i]',
    '[class*="card" i]',
]


def _progress(callback: ProgressCallback, message: str) -> None:
    if callback:
        callback(message)


def scrape_louveapp_schedules(page: Page, progress: ProgressCallback = None) -> list[LouveAppSchedule]:
    schedules: list[LouveAppSchedule] = []
    _progress(progress, "Lendo tela inicial...")
    schedules.extend(_extract_from_current_page(page, "pagina_inicial"))

    for menu_text in MENU_TEXTS:
        _progress(progress, f"Tentando menu: {menu_text}")
        if _try_click_menu(page, menu_text):
            schedules.extend(_extract_from_current_page(page, f"menu_{menu_text}"))

    base_url = page.url.split("#")[0]
    for route in ROUTES:
        route_url = f"{base_url}{route}"
        _progress(progress, f"Testando rota: {route}")
        try:
            page.goto(route_url, wait_until="domcontentloaded", timeout=20_000)
            _wait_for_quiet_page(page)
            schedules.extend(_extract_from_current_page(page, f"rota_{route.strip('#/')}"))
        except Exception:
            logger.exception("Erro ao testar rota LouveApp: %s", route_url)

    return dedupe_schedules(schedules)


def parse_louveapp_api_schedule_records(records: list[dict]) -> list[LouveAppSchedule]:
    schedules: list[LouveAppSchedule] = []
    for record in records:
        try:
            payload = json.loads(record.get("body") or "{}")
        except json.JSONDecodeError:
            continue
        docs = payload.get("docs") if isinstance(payload, dict) else payload
        if not isinstance(docs, list):
            continue
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            schedules.extend(_schedule_doc_to_rows(doc, record.get("url", "")))
    return _dedupe_api_rows(schedules)


def _dedupe_api_rows(rows: list[LouveAppSchedule]) -> list[LouveAppSchedule]:
    unique: list[LouveAppSchedule] = []
    seen: set[tuple[str, str, str, str, str, str, str]] = set()
    for row in rows:
        key = (
            row.category,
            row.title,
            row.date_text,
            row.time_text,
            row.role,
            row.person_name,
            row.raw_json,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _schedule_doc_to_rows(doc: dict, page_url: str) -> list[LouveAppSchedule]:
    title = str(doc.get("descricao") or "").strip()
    date_text, time_text = _date_time_from_iso(str(doc.get("data") or ""))
    ministry_data = doc.get("ministerio") if isinstance(doc.get("ministerio"), dict) else {}
    ministry = str(ministry_data.get("nome") or "").strip()
    songs = _songs_from_doc(doc)
    people = _people_from_doc(doc)
    people_text = "; ".join(
        f"{person['name']} ({person['role']})" if person["role"] else person["name"]
        for person in people
        if person["name"]
    )
    songs_text = "; ".join(
        _song_summary(song)
        for song in songs
        if song["title"]
    )
    raw_json = json.dumps(doc, ensure_ascii=False)
    raw_text = "\n".join(
        part
        for part in [
            title,
            f"Data: {date_text}",
            f"Hora: {time_text}",
            f"Ministerio: {ministry}",
            f"Pessoas: {people_text}",
            f"Musicas: {songs_text}",
            f"Observacoes: {doc.get('observacoes') or ''}",
        ]
        if part and not part.endswith(": ")
    )

    rows = [
        LouveAppSchedule(
            category="api_schedule",
            title=title,
            date_text=date_text,
            time_text=time_text,
            ministry=ministry,
            role="Resumo",
            person_name="",
            people_text=people_text,
            raw_text=raw_text,
            page_url=_safe_page_url(page_url),
            raw_json=raw_json,
            imported_at=now_text(),
        )
    ]

    for person in people:
        person_raw = json.dumps(
            {"schedule_id": doc.get("_id"), "schedule_title": title, "person": person, "songs": songs},
            ensure_ascii=False,
        )
        rows.append(
            LouveAppSchedule(
                category="api_schedule_user",
                title=title,
                date_text=date_text,
                time_text=time_text,
                ministry=ministry,
                role=person["role"],
                person_name=person["name"],
                people_text=people_text,
                raw_text=f"{title}\n{date_text} {time_text}\n{person['name']} - {person['role']}\nMusicas: {songs_text}",
                page_url=_safe_page_url(page_url),
                raw_json=person_raw,
                imported_at=now_text(),
            )
        )

    for song in songs:
        song_raw = json.dumps(
            {"schedule_id": doc.get("_id"), "schedule_title": title, "song": song},
            ensure_ascii=False,
        )
        rows.append(
            LouveAppSchedule(
                category="api_schedule_song",
                title=f"{title} - {song['title']}" if song["title"] else title,
                date_text=date_text,
                time_text=time_text,
                ministry=ministry,
                role="Musica",
                person_name=song.get("artist", ""),
                people_text=people_text,
                raw_text=(
                    f"{title}\n{date_text} {time_text}\n"
                    f"Musica: {song['title']}\n"
                    f"Grupo/Cantor: {song.get('artist', '')}\n"
                    f"Tom: {song['key']}"
                ),
                page_url=_safe_page_url(page_url),
                raw_json=song_raw,
                imported_at=now_text(),
            )
        )

    return rows


def _date_time_from_iso(value: str) -> tuple[str, str]:
    if not value:
        return "", ""
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed.strftime("%d/%m/%Y"), value[11:16] if len(value) >= 16 else parsed.strftime("%H:%M")
    except ValueError:
        date_part = value[:10]
        time_part = value[11:16] if len(value) >= 16 else ""
        if len(date_part) == 10 and "-" in date_part:
            year, month, day = date_part.split("-")
            return f"{day}/{month}/{year}", time_part
        return value, time_part


def _people_from_doc(doc: dict) -> list[dict[str, str]]:
    people: list[dict[str, str]] = []
    for assignment in doc.get("usuarios") or []:
        if not isinstance(assignment, dict):
            continue
        user = assignment.get("usuario") if isinstance(assignment.get("usuario"), dict) else {}
        name = str(user.get("nome") or "").strip()
        instruments = assignment.get("instrumentos") or []
        roles = [
            str(instrument.get("nome") or "").strip()
            for instrument in instruments
            if isinstance(instrument, dict) and str(instrument.get("nome") or "").strip()
        ]
        if name:
            people.append({"name": name, "role": ", ".join(roles)})
    return people


def _songs_from_doc(doc: dict) -> list[dict[str, str]]:
    songs: list[dict[str, str]] = []
    for entry in doc.get("musicasEscala") or []:
        if not isinstance(entry, dict):
            continue
        music = entry.get("musica") if isinstance(entry.get("musica"), dict) else {}
        original = music.get("musicaOriginal") if isinstance(music.get("musicaOriginal"), dict) else {}
        artist = original.get("artista") if isinstance(original.get("artista"), dict) else {}
        title = str(original.get("nome") or music.get("nome") or "").strip()
        artist_name = str(artist.get("nome") or "").strip()
        version_id = str(entry.get("versao") or "")
        version = _find_song_version(music.get("versoes") or [], version_id)
        key = str(version.get("tom") or "").strip() if version else ""
        songs.append(
            {
                "title": title,
                "artist": artist_name,
                "key": key,
                "version": str(version.get("nomeVersao") or "") if version else "",
            }
        )
    return songs


def _song_summary(song: dict[str, str]) -> str:
    parts = [song.get("title", "")]
    if song.get("artist"):
        parts.append(song["artist"])
    if song.get("key"):
        parts.append(f"Tom: {song['key']}")
    return " | ".join(part for part in parts if part)


def _find_song_version(versions: list, version_id: str) -> dict:
    if not isinstance(versions, list):
        return {}
    for version in versions:
        if isinstance(version, dict) and str(version.get("_id") or "") == version_id:
            return version
    for version in versions:
        if isinstance(version, dict):
            return version
    return {}


def _safe_page_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    safe_query = {}
    for key in ("page", "limit", "offset"):
        if key in query:
            safe_query[key] = query[key][-1]
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(safe_query), ""))


def _try_click_menu(page: Page, text: str) -> bool:
    locators = [
        page.get_by_text(text, exact=False).first,
        page.locator(f'a:has-text("{text}")').first,
        page.locator(f'button:has-text("{text}")').first,
        page.locator(f'[role="menuitem"]:has-text("{text}")').first,
    ]
    for locator in locators:
        try:
            locator.wait_for(state="visible", timeout=1_500)
            locator.click(timeout=3_000)
            _wait_for_quiet_page(page)
            return True
        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue
    return False


def _wait_for_quiet_page(page: Page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=6_000)
    except PlaywrightTimeoutError:
        pass
    try:
        page.wait_for_timeout(700)
    except Exception:
        pass


def _extract_from_current_page(page: Page, category: str) -> list[LouveAppSchedule]:
    page_url = page.url
    schedules: list[LouveAppSchedule] = []
    for selector in CONTENT_SELECTORS:
        try:
            locator = page.locator(selector)
            count = min(locator.count(), 80)
            for index in range(count):
                try:
                    raw_text = locator.nth(index).inner_text(timeout=1_000)
                except Exception:
                    continue
                schedule = parse_schedule_text(raw_text, page_url=page_url, category=category)
                if schedule:
                    schedules.append(schedule)
        except Exception:
            continue

    if schedules:
        return dedupe_schedules(schedules)

    try:
        body_text = page.locator("body").inner_text(timeout=3_000)
        return parse_body_fallback(body_text, page_url=page_url, category=f"{category}_fallback")
    except Exception:
        logger.exception("Falha ao aplicar fallback de leitura do body")
        return []
