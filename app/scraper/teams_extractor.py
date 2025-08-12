"""
Сбор ссылок команд со страниц лиг.
"""
from typing import List, Tuple
from urllib.parse import urljoin
from playwright.async_api import Page

from app.config import BASE_URL, DEF_TIMEOUT_MS
from app.scraper.navigation import goto_smart, wait_stable_count
from app.scraper.match_parser import accept_cookies_if_any


async def get_team_links(page: Page, league_url: str) -> List[Tuple[str, str]]:
    """Список (Название, URL) команд со страницы конкретной лиги."""
    async def league_ready(p: Page):
        await accept_cookies_if_any(p)
        await p.wait_for_selector("a[href*='/team/']", timeout=DEF_TIMEOUT_MS)
        await wait_stable_count(p, "a[href*='/team/']", min_count=10, stable_ms=600, overall_timeout_ms=DEF_TIMEOUT_MS)

    await goto_smart(page, league_url, league_ready, nav_timeout_ms=DEF_TIMEOUT_MS)

    raw = await page.eval_on_selector_all(
        "a[href*='/team/']",
        """els => els.map(a => [a.textContent?.trim() || "", a.getAttribute('href')])"""
    )

    seen, out = set(), []
    for name, href in raw:
        if not name or not href or "/team/" not in href:
            continue
        url = urljoin(BASE_URL, href)
        if url in seen:
            continue
        seen.add(url)
        out.append((name, url))
    return out
