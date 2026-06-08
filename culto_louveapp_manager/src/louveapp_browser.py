from __future__ import annotations

from pathlib import Path
import re
from typing import Callable, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from src.config import DEBUG_DIR, LOUVEAPP_LOGIN_URL, get_headless, get_slow_mo_ms, validate_louveapp_credentials
from src.database import Database
from src.logger import get_logger
from src.louveapp_scraper import parse_louveapp_api_schedule_records, scrape_louveapp_schedules
from src.models import ImportResult, now_text
from src.parser import dedupe_schedules


logger = get_logger(__name__)


ProgressCallback = Optional[Callable[[str], None]]

EMAIL_SELECTORS = [
    'input[type="email"]',
    'input[name="email"]',
    'input[id="email"]',
    'input[formcontrolname="email"]',
    'input[placeholder*="email" i]',
    'input[placeholder*="usuario" i]',
    'input[placeholder*="usuário" i]',
    'input[autocomplete="email"]',
]

PASSWORD_SELECTORS = [
    'input[type="password"]',
    'input[name="password"]',
    'input[name="current-password"]',
    'input[id="current-password"]',
    'input[formcontrolname="password"]',
    'input[placeholder*="senha" i]',
    'input[autocomplete="current-password"]',
]

SUBMIT_SELECTORS = [
    'button:has-text("Entrar")',
    'button:has-text("Login")',
    'button:has-text("Acessar")',
    'button[type="submit"]',
    'input[type="submit"]',
    'input.submitBtn',
    '[role="button"]:has-text("Entrar")',
    '[aria-label*="Entrar" i]',
    '[class*="submit" i]',
]


def _progress(callback: ProgressCallback, message: str) -> None:
    if callback:
        callback(message)


def _safe_label(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", label).strip("_") or "debug"


def save_debug_artifacts(page: Optional[Page], label: str) -> dict[str, str]:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = now_text().replace(":", "-").replace(" ", "_")
    safe_label = _safe_label(label)
    html_path = DEBUG_DIR / f"{timestamp}_{safe_label}.html"
    png_path = DEBUG_DIR / f"{timestamp}_{safe_label}.png"
    saved: dict[str, str] = {}
    if page is None:
        return saved
    try:
        html_path.write_text(page.content(), encoding="utf-8")
        saved["html"] = str(html_path)
    except Exception:
        logger.exception("Falha ao salvar HTML de debug")
    try:
        page.screenshot(path=str(png_path), full_page=True)
        saved["screenshot"] = str(png_path)
    except Exception:
        logger.exception("Falha ao salvar screenshot de debug")
    return saved


def attach_louveapp_api_capture(page: Page, records: list[dict]) -> None:
    def handler(response) -> None:
        url = response.url
        if "api.louveapp.com.br" not in url.lower() or "/schedules" not in url.lower():
            return
        if response.status >= 400:
            return
        content_type = response.headers.get("content-type", "").lower()
        if "json" not in content_type:
            return
        try:
            records.append(
                {
                    "url": url,
                    "status": response.status,
                    "body": response.text(),
                    "request_headers": _request_headers_for_replay(response.request.headers),
                }
            )
        except Exception:
            logger.exception("Falha ao capturar resposta de escalas da API LouveApp")

    page.on("response", handler)


def fetch_remaining_schedule_pages(page: Page, records: list[dict], progress: ProgressCallback = None) -> None:
    seen_urls = {record.get("url", "") for record in records}
    for record in list(records):
        try:
            import json

            payload = json.loads(record.get("body") or "{}")
        except Exception:
            continue
        total_pages = int(payload.get("totalPages") or 1)
        current_page = int(payload.get("page") or 1)
        limit = int(payload.get("limit") or 0)
        if total_pages <= current_page:
            continue
        for page_number in range(current_page + 1, total_pages + 1):
            url = _url_with_page(record.get("url", ""), page_number, limit)
            if not url or url in seen_urls:
                continue
            _progress(progress, f"Buscando pagina {page_number}/{total_pages} das escalas LouveApp...")
            try:
                response = page.request.get(url, headers=record.get("request_headers") or {}, timeout=30_000)
                if response.status >= 400:
                    continue
                records.append(
                    {
                        "url": url,
                        "status": response.status,
                        "body": response.text(),
                        "request_headers": record.get("request_headers") or {},
                    }
                )
                seen_urls.add(url)
            except Exception:
                logger.exception("Falha ao buscar pagina adicional de escalas LouveApp")


def _request_headers_for_replay(headers: dict) -> dict:
    blocked = {
        "accept-encoding",
        "connection",
        "content-length",
        "host",
        "referer",
    }
    return {key: value for key, value in headers.items() if key.lower() not in blocked}


def _url_with_page(url: str, page_number: int, limit: int) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if limit:
        query["offset"] = [str((page_number - 1) * limit)]
        query["limit"] = [str(limit)]
    else:
        query["page"] = [str(page_number)]
    query.pop("page", None)
    encoded_query = urlencode({key: values[-1] for key, values in query.items()})
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", encoded_query, ""))


class LouveAppBrowserSession:
    def __init__(self, email: str, password: str, headless: bool, slow_mo_ms: int) -> None:
        self.email = email
        self.password = password
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self.playwright = None
        self.browser = None
        self.context = None
        self.page: Optional[Page] = None

    def start(self) -> Page:
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo_ms,
            )
            self.context = self.browser.new_context(locale="pt-BR")
            self.page = self.context.new_page()
            return self.page
        except Exception:
            logger.exception("Falha ao abrir navegador Playwright")
            self.close()
            raise RuntimeError("Falha ao abrir navegador. Confira se executou: playwright install chromium")

    def login(self, progress: ProgressCallback = None) -> Page:
        page = self.page or self.start()
        try:
            _progress(progress, "Abrindo LouveApp...")
            page.goto(LOUVEAPP_LOGIN_URL, wait_until="domcontentloaded", timeout=45_000)
            self._wait_for_login_or_app(page)
            if self._login_appears_complete(page):
                _progress(progress, "Sessao LouveApp ja autenticada. Procurando escalas...")
                return page
            self._fill_login_fields(page)
            _progress(progress, "Enviando login...")
            self._submit_login(page)
            self._wait_for_login(page)
            _progress(progress, "Login concluido. Procurando escalas...")
            return page
        except Exception as exc:
            save_debug_artifacts(page, "louveapp_login_error")
            logger.exception("Erro de login no LouveApp")
            raise RuntimeError(f"Login no LouveApp nao foi concluido: {exc}") from exc

    def _fill_first(self, page: Page, selectors: list[str], value: str, label: str) -> None:
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=4_000)
                locator.fill(value, timeout=5_000)
                return
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                locator.wait_for(state="attached", timeout=2_000)
                locator.fill(value, timeout=5_000, force=True)
                return
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue
        if self._login_appears_complete(page):
            return
        raise RuntimeError(f"Nao foi possivel encontrar {label}.")

    def _click_first(self, page: Page, selectors: list[str], label: str) -> None:
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=3_000)
                locator.click(timeout=5_000)
                return
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue
        raise RuntimeError(f"Nao foi possivel encontrar {label}.")

    def _submit_login(self, page: Page) -> None:
        if self._login_appears_complete(page):
            return

        try:
            self._click_first(page, SUBMIT_SELECTORS, "botao de entrada")
            return
        except RuntimeError:
            pass

        for submit_action in (
            self._press_enter_on_password,
            self._dispatch_submit_event,
            self._click_flutter_login_area,
        ):
            if self._login_appears_complete(page):
                return
            try:
                submit_action(page)
                self._wait_for_login_or_app(page, timeout_ms=6_000)
                if self._login_appears_complete(page):
                    return
            except Exception:
                continue

        if self._login_appears_complete(page):
            return
        raise RuntimeError("Nao foi possivel acionar o botao de entrada.")

    def _press_enter_on_password(self, page: Page) -> None:
        for selector in PASSWORD_SELECTORS:
            locator = page.locator(selector).first
            try:
                locator.focus(timeout=1_500)
                page.keyboard.press("Enter")
                return
            except Exception:
                continue
        page.keyboard.press("Enter")

    def _dispatch_submit_event(self, page: Page) -> None:
        page.evaluate(
            """
            () => {
                const submit = document.querySelector('input[type="submit"], input.submitBtn, button[type="submit"], button');
                if (submit) {
                    submit.click();
                    return;
                }
                const form = document.querySelector('form');
                if (form) {
                    if (typeof form.requestSubmit === 'function') {
                        form.requestSubmit();
                    } else {
                        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                    }
                }
            }
            """
        )

    def _click_flutter_login_area(self, page: Page) -> None:
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        width = viewport["width"]
        height = viewport["height"]
        # Flutter Web paints the LouveApp primary button on canvas, outside normal DOM buttons.
        page.mouse.click(width * 0.81, height * 0.55)

    def _wait_for_login_or_app(self, page: Page, timeout_ms: int = 15_000) -> None:
        try:
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            pass
        try:
            page.wait_for_timeout(700)
        except Exception:
            pass

    def _login_appears_complete(self, page: Page) -> bool:
        current_url = page.url.lower()
        if "#/login" not in current_url and "/login" not in current_url:
            return True

        try:
            visible_password_count = page.locator('input[type="password"]:visible').count()
            if visible_password_count == 0:
                body_text = page.locator("body").inner_text(timeout=800).casefold()
                logged_in_terms = (
                    "minhas escalas",
                    "ministérios",
                    "ministerios",
                    "repertório",
                    "repertorio",
                    "configurações",
                    "configuracoes",
                    "visão geral",
                    "visao geral",
                )
                if any(term in body_text for term in logged_in_terms):
                    return True
        except Exception:
            return False

        return False

    def _fill_login_fields(self, page: Page) -> None:
        try:
            self._fill_first(page, EMAIL_SELECTORS, self.email, "campo de e-mail")
            self._fill_first(page, PASSWORD_SELECTORS, self.password, "campo de senha")
            return
        except RuntimeError:
            if self._login_appears_complete(page):
                return
            self._fill_flutter_login_fields(page)

    def _fill_flutter_login_fields(self, page: Page) -> None:
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        width = viewport["width"]
        height = viewport["height"]
        email_x = width * 0.81
        email_y = height * 0.33
        password_x = width * 0.81
        password_y = height * 0.415

        self._click_select_and_type(page, email_x, email_y, self.email)
        self._click_select_and_type(page, password_x, password_y, self.password)

    def _click_select_and_type(self, page: Page, x: float, y: float, value: str) -> None:
        page.mouse.click(x, y)
        page.wait_for_timeout(200)
        page.keyboard.press("Control+A")
        page.keyboard.type(value, delay=20)

    def _wait_for_login(self, page: Page) -> None:
        try:
            page.wait_for_load_state("networkidle", timeout=20_000)
        except PlaywrightTimeoutError:
            pass

        for _ in range(20):
            if self._login_appears_complete(page):
                return
            page.wait_for_timeout(500)
        raise RuntimeError("A tela de login continuou visivel apos enviar as credenciais.")

    def close(self) -> None:
        for resource in (self.context, self.browser):
            try:
                if resource:
                    resource.close()
            except Exception:
                logger.exception("Falha ao fechar recurso Playwright")
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            logger.exception("Falha ao encerrar Playwright")


def import_louveapp_schedules(
    progress: ProgressCallback = None,
    clear_existing: bool = False,
) -> ImportResult:
    logger.info("Inicio da importacao LouveApp")
    database = Database()
    email, password = validate_louveapp_credentials()
    session = LouveAppBrowserSession(email, password, get_headless(), get_slow_mo_ms())
    api_schedule_records: list[dict] = []
    try:
        page = session.start()
        attach_louveapp_api_capture(page, api_schedule_records)
        session.login(progress)
        _progress(progress, "Aguardando dados da API LouveApp...")
        page.wait_for_timeout(5_000)
        fetch_remaining_schedule_pages(page, api_schedule_records, progress)
        api_schedules = parse_louveapp_api_schedule_records(api_schedule_records)
        schedules = api_schedules
        if api_schedules:
            _progress(progress, f"{len(api_schedules)} registro(s) de escala lido(s) pela API LouveApp.")
        else:
            _progress(progress, "API de escalas nao retornou dados. Tentando leitura visual da interface...")
            visual_schedules = scrape_louveapp_schedules(page, progress)
            fetch_remaining_schedule_pages(page, api_schedule_records, progress)
            api_schedules = parse_louveapp_api_schedule_records(api_schedule_records)
            schedules = dedupe_schedules([*visual_schedules, *api_schedules])
        if not schedules:
            artifacts = save_debug_artifacts(page, "louveapp_no_schedules_found")
            message = (
                "Nenhuma escala foi encontrada. Arquivos de debug foram salvos em data/debug "
                "para ajustar os seletores se a interface do LouveApp mudou."
            )
            if artifacts:
                message += f" HTML: {Path(artifacts.get('html', '')).name}"
            database.insert_import_log("louveapp", "warning", message)
            logger.warning(message)
            return ImportResult("louveapp", "warning", message, 0, 0, [])

        result = database.save_louveapp_schedules(schedules, clear_existing=clear_existing)
        logger.info("Fim da importacao LouveApp: %s", result.message)
        return result
    except Exception as exc:
        logger.exception("Falha na importacao LouveApp")
        message = str(exc)
        database.insert_import_log("louveapp", "error", message)
        return ImportResult("louveapp", "error", message, 0, 0, [message])
    finally:
        session.close()
