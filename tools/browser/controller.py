from __future__ import annotations

import webbrowser
from dataclasses import dataclass
from urllib.parse import quote_plus

from core.config import Settings


@dataclass(slots=True)
class BrowserController:
    settings: Settings | None = None

    def open_url(self, url: str) -> bool:
        return bool(webbrowser.open(url))

    def google_search(self, query: str) -> str:
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        if not self.open_url(url):
            raise RuntimeError("Browser did not accept Google search URL.")
        return url

    def open_youtube(self, query: str | None = None) -> str:
        url = "https://www.youtube.com" if not query else f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        if not self.open_url(url):
            raise RuntimeError("Browser did not accept YouTube URL.")
        return url

    def open_github(self, query: str | None = None) -> str:
        url = "https://github.com" if not query else f"https://github.com/search?q={quote_plus(query)}"
        if not self.open_url(url):
            raise RuntimeError("Browser did not accept GitHub URL.")
        return url

    async def navigate_with_playwright(self, url: str) -> str:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed. Install it and run 'playwright install'.") from exc
        headless = self.settings.browser_headless if self.settings else False
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()
            await page.goto(url)
            title = await page.title()
            await browser.close()
            return title
