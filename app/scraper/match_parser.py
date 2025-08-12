"""
Парсинг страницы команды и матча.

"""
from typing import Optional, Dict, List, Tuple
from urllib.parse import urljoin
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from app.config import (
    BASE_URL,
    COOKIE_BTN_TIMEOUT_MS,
    WAIT_EVENTLINKS_TIMEOUT_MS,
    STAT_ROW_TIMEOUT_MS,
    DEF_TIMEOUT_MS,
    FORCE_SCROLL_STATS,
)
from app.scraper.navigation import wait_stable_count
from app.utils import (
    tiny_sleep,
    normalize_match_stats_url,
    extract_match_id,
    to_int_safe,
    clean_team_name,
)


async def accept_cookies_if_any(page: Page):
    """Кликаем согласие с куки, если баннер всплыл."""
    for sel in [
        "button:has-text('Принять')",
        "button:has-text('Согласиться')",
        "button:has-text('I Accept')",
        "div[data-testid='banner'] button",
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=COOKIE_BTN_TIMEOUT_MS):
                await btn.click()
                await tiny_sleep()
                break
        except Exception:
            pass


async def wait_team_page_ready(page: Page):
    """Готовность страницы команды: вкладка «Последние результаты» + видимые ссылки матчей."""
    await accept_cookies_if_any(page)
    try:
        ear = page.locator(
            "//div[contains(@class,'tabs__ear') and normalize-space()='Последние результаты']"
        ).first
        if await ear.is_visible(timeout=1500):
            await ear.click()
            await tiny_sleep()
    except Exception:
        pass

    await page.wait_for_selector("a.eventRowLink:visible", timeout=WAIT_EVENTLINKS_TIMEOUT_MS)
    await wait_stable_count(
        page,
        "a.eventRowLink:visible",
        min_count=1,
        stable_ms=600,
        overall_timeout_ms=WAIT_EVENTLINKS_TIMEOUT_MS,
    )


async def get_second_decade_event_links(page: Page) -> List[str]:
    """Берём ссылки на 10 нужных матчей (обычно второй десяток: индексы 10..19)."""
    await wait_team_page_ready(page)

    rows = page.locator("a.eventRowLink:visible")
    count = await rows.count()

    if count >= 20:
        start, end = 10, 20
    else:
        start = max(0, count - 10)
        end = count

    links: List[str] = []
    for i in range(start, end):
        href = await rows.nth(i).get_attribute("href")
        if not href:
            continue
        links.append(urljoin(BASE_URL, href))

    return [normalize_match_stats_url(h) for h in links]


async def wait_stats_ready(page: Page):
    """Готовность страницы статистики матча (строка «Угловые»)."""
    await accept_cookies_if_any(page)
    try:
        stats_tab = page.locator("a:has-text('Статистика')").first
        if await stats_tab.is_visible(timeout=1500):
            await stats_tab.click()
            await tiny_sleep()
    except Exception:
        pass

    # RAW-строка: внутри JS используются регэкспы \d и т.п.
    await page.wait_for_function(
        r"""
        () => {
            const qa = (sel, root=document)=>Array.from(root.querySelectorAll(sel));
            const q  = (sel, root=document)=>root.querySelector(sel);

            // Новая разметка
            const cats = qa('[data-testid="wcl-statistics-category"]');
            for (const cat of cats) {
                const t = (q('strong', cat)?.textContent || '').trim();
                if (/углов/i.test(t)) {
                    const row = cat.parentElement;
                    const vals = row ? qa('[data-testid="wcl-statistics-value"] strong', row) : [];
                    if (vals.length >= 2) {
                        const a = (vals[0].textContent||'').match(/\d+/);
                        const b = (vals[1].textContent||'').match(/\d+/);
                        if (a && b) return true;
                    }
                }
            }
            // Старая разметка — ищем любую строку stat__row, где встречается "Углов"
            const rows = qa('div.stat__row');
            for (const r of rows) {
                const txt = (r.textContent || '').toLowerCase();
                if (txt.includes('углов')) {
                    const home = q('.stat__homeValue, .stat__value--home', r);
                    const away = q('.stat__awayValue, .stat__value--away', r);
                    const hv = home && (home.textContent||'').match(/\d+/);
                    const av = away && (away.textContent||'').match(/\d+/);
                    if (hv && av) return true;
                }
            }
            return false;
        }
        """,
        timeout=STAT_ROW_TIMEOUT_MS,
    )


async def get_team_names(page: Page) -> Tuple[Optional[str], Optional[str]]:
    """Достаём имена команд по разным вариантам вёрстки и чистим от счёта."""
    # RAW-строка: внутри JS регэксп с \s
    names = await page.evaluate(
        r"""
        () => {
            const pick = (sels) => {
                for (const s of sels) {
                    const el = document.querySelector(s);
                    const t = el && (el.textContent || el.getAttribute('title') || '').trim();
                    if (t) return t;
                }
                return null;
            };
            const home = pick([
                '[data-testid="wcl-participant-home"] [data-testid="wcl-participant-name"]',
                '[data-testid="wcl-participantHomeName"]',
                '[data-testid="wcl-participant-home-name"]',
                '.duelParticipants .home [class*="participantName"]',
                '.duelParticipants .home a[title]'
            ]);
            const away = pick([
                '[data-testid="wcl-participant-away"] [data-testid="wcl-participant-name"]',
                '[data-testid="wcl-participantAwayName"]',
                '[data-testid="wcl-participant-away-name"]',
                '.duelParticipants .away [class*="participantName"]',
                '.duelParticipants .away a[title]'
            ]);
            let title = document.querySelector('meta[property="og:title"]')?.content || document.title || '';
            title = title.replace(/\s+\|.*$/, '').trim();
            const sepMatch = title.match(/\s([-–—])\s/);
            let tHome = null, tAway = null;
            if (sepMatch) {
                const parts = title.split(sepMatch[0]);
                if (parts.length >= 2) {
                    tHome = parts[0].trim();
                    tAway = parts[1].trim();
                }
            }
            return {home, away, tHome, tAway};
        }
        """
    )
    home = names.get("home") or names.get("tHome")
    away = names.get("away") or names.get("tAway")
    return clean_team_name(home), clean_team_name(away)


async def extract_corners_by_wcl(page: Page) -> Optional[Tuple[int, int]]:
    """Парсим угловые по новой вёрстке (wcl-*)."""
    try:
        await page.wait_for_selector('[data-testid="wcl-statistics-category"]', timeout=STAT_ROW_TIMEOUT_MS)
    except Exception:
        return None

    # RAW-строка: внутри JS регэкспы \d
    data = await page.evaluate(
        r"""
        () => {
           const qa = (sel, root=document)=>Array.from(root.querySelectorAll(sel));
           const cats = qa('[data-testid="wcl-statistics-category"]');
           let row = null;
           for (const cat of cats) {
              const t = (cat.querySelector('strong')?.textContent || '').trim();
              if (/углов/i.test(t)) { row = cat.parentElement; break; }
           }
           if (!row) return null;
           const vals = qa('[data-testid="wcl-statistics-value"] strong', row);
           if (vals.length < 2) return null;
           const toInt = s => {
              const m = String(s||'').match(/\d+/);
              return m ? parseInt(m[0],10) : null;
           };
           return {home: toInt(vals[0].textContent), away: toInt(vals[1].textContent)};
        }
        """
    )
    if not data:
        return None
    return data["home"], data["away"]


async def parse_match_corners(page: Page) -> Optional[Dict]:
    """Парсим «Угловые» на вкладке статистики матча и возвращаем словарь значений."""
    await wait_stats_ready(page)

    vals = await extract_corners_by_wcl(page)
    if not vals and FORCE_SCROLL_STATS:
        try:
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(300)
            await page.mouse.wheel(0, -2000)
            await page.wait_for_timeout(200)
        except Exception:
            pass
        try:
            await wait_stats_ready(page)
        except Exception:
            pass
        vals = await extract_corners_by_wcl(page)

    if vals:
        home_corners, away_corners = vals
    else:
        try:
            row = page.locator(
                "//div[contains(@class,'stat__row')][.//div[normalize-space()='Угловые']]"
            ).first
            await row.wait_for(state="visible", timeout=STAT_ROW_TIMEOUT_MS)
            home_val = await row.locator(
                ".//div[contains(@class,'stat__homeValue') or contains(@class,'stat__value--home')]"
            ).inner_text()
            away_val = await row.locator(
                ".//div[contains(@class,'stat__awayValue') or contains(@class,'stat__value--away')]"
            ).inner_text()
            home_corners = to_int_safe(home_val)
            away_corners = to_int_safe(away_val)
        except PlaywrightTimeoutError:
            return None

    home_team, away_team = await get_team_names(page)
    return {
        "match_id": extract_match_id(page.url),
        "url": page.url,
        "home_team": clean_team_name(home_team),
        "away_team": clean_team_name(away_team),
        "home_corners": home_corners,
        "away_corners": away_corners,
    }
