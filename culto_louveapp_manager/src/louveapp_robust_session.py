from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.logger import get_logger
from src.louveapp_browser import LouveAppBrowserSession


logger = get_logger(__name__)


class LouveAppRobustBrowserSession(LouveAppBrowserSession):
    def _submit_login(self, page) -> None:
        if self._login_appears_complete(page):
            return

        attempts = (
            self._click_visible_submit_button,
            self._press_enter_on_password,
            self._press_tab_then_enter,
            self._dispatch_submit_event,
            self._click_flutter_login_candidates,
        )
        for attempt in attempts:
            try:
                attempt(page)
                self._wait_for_login_or_app(page, timeout_ms=8_000)
                if self._login_appears_complete(page):
                    return
            except Exception:
                logger.exception("Tentativa de login LouveApp falhou: %s", getattr(attempt, "__name__", attempt))
                continue

        raise RuntimeError("Nao foi possivel acionar o botao de entrada.")

    def _click_visible_submit_button(self, page) -> None:
        selectors = [
            'button:has-text("Entrar")',
            'button:has-text("Acessar")',
            'button:has-text("Login")',
            'button[type="submit"]',
            'input[type="submit"]',
            '[role="button"]:has-text("Entrar")',
            '[role="button"]:has-text("Acessar")',
            '[aria-label*="Entrar" i]',
            '[aria-label*="Acessar" i]',
        ]
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=1_500)
                locator.click(timeout=3_000, force=True)
                return
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue
        raise RuntimeError("Nenhum botao HTML visivel de login foi encontrado.")

    def _press_tab_then_enter(self, page) -> None:
        page.keyboard.press("Tab")
        page.wait_for_timeout(150)
        page.keyboard.press("Tab")
        page.wait_for_timeout(150)
        page.keyboard.press("Enter")

    def _click_flutter_login_candidates(self, page) -> None:
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        width = viewport["width"]
        height = viewport["height"]
        candidates = [
            (0.81, 0.55),
            (0.81, 0.58),
            (0.80, 0.61),
            (0.78, 0.55),
            (0.85, 0.55),
            (0.50, 0.72),
        ]
        for x_ratio, y_ratio in candidates:
            page.mouse.click(width * x_ratio, height * y_ratio)
            page.wait_for_timeout(1_000)
            if self._login_appears_complete(page):
                return
        raise RuntimeError("Cliques nas posicoes provaveis do botao Flutter nao concluiram o login.")
