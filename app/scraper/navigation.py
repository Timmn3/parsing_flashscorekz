"""
Навигация и ожидания стабильности DOM.
"""
import time
from playwright.async_api import Page

async def goto_smart(page: Page, url: str, await_ready, nav_timeout_ms: int):
    """
    Быстрая навигация (wait_until='commit'), затем ждём ПРИЗНАКИ ГОТОВНОСТИ через await_ready(page).
    """
    await page.goto(url, wait_until="commit", timeout=nav_timeout_ms)
    await await_ready(page)


async def wait_stable_count(page: Page, selector: str, min_count: int = 1, stable_ms: int = 600, overall_timeout_ms: int = 8000):
    """
    Ждём, когда количество элементов по селектору станет >= min_count и стабилизируется минимум stable_ms.
    """
    deadline = time.monotonic() + overall_timeout_ms / 1000.0
    last_count = -1
    stable_since: float | None = None

    while time.monotonic() < deadline:
        try:
            count = await page.locator(selector).count()
        except Exception:
            count = 0

        now = time.monotonic()
        if count >= min_count:
            if count == last_count:
                if stable_since is None:
                    stable_since = now
                elif (now - stable_since) * 1000 >= stable_ms:
                    return
            else:
                stable_since = now
        else:
            stable_since = None

        last_count = count
        await page.wait_for_timeout(150)
