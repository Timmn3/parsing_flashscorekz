"""
Основной пайплайн: сбор команд, парсинг матчей и сохранение результатов.
"""
import asyncio
from typing import Dict, List, Tuple

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app import config
from app.scraper.teams_extractor import get_team_links
from app.scraper.match_parser import (
    wait_team_page_ready,
    get_second_decade_event_links,
    parse_match_corners,
)
from app.scraper.navigation import goto_smart
from app.services.aggregator import update_team_agg, compute_sorted_table, write_averages_csv
from app.utils import norm_for_compare, tiny_sleep, normalize_match_stats_url


async def process_team(
    context: BrowserContext,
    team_name: str,
    team_link: str,
    teams_agg: Dict[str, Dict],
    agg_lock: asyncio.Lock,
) -> int:
    """Обрабатываем одну команду: собираем до N матчей и агрегируем угловые."""
    page: Page = await context.new_page()
    page.set_default_navigation_timeout(config.NAV_TIMEOUT_MS)
    page.set_default_timeout(config.DEF_TIMEOUT_MS)

    taken = 0
    try:
        await goto_smart(page, team_link, wait_team_page_ready, config.NAV_TIMEOUT_MS)

        candidates = await get_second_decade_event_links(page)
        if not candidates:
            print(f"   - [{team_name}] нет ссылок eventRowLink")
            return 0

        for href in candidates:
            if taken >= config.MATCHES_PER_TEAM:
                break
            url = normalize_match_stats_url(href)
            try:
                await goto_smart(page, url, lambda p: p.wait_for_timeout(100), config.NAV_TIMEOUT_MS)
                await tiny_sleep()

                data = await parse_match_corners(page)
                if not data or data["home_corners"] is None or data["away_corners"] is None:
                    continue

                src = norm_for_compare(team_name)
                home_n = norm_for_compare(data.get("home_team") or "")
                away_n = norm_for_compare(data.get("away_team") or "")

                if src == home_n:
                    team_c, opp_c = data["home_corners"], data["away_corners"]
                elif src == away_n:
                    team_c, opp_c = data["away_corners"], data["home_corners"]
                else:
                    if src and (src in home_n):
                        team_c, opp_c = data["home_corners"], data["away_corners"]
                    elif src and (src in away_n):
                        team_c, opp_c = data["away_corners"], data["home_corners"]
                    else:
                        continue

                async with agg_lock:
                    update_team_agg(teams_agg, team_name, team_c, opp_c)

                taken += 1
            except Exception:
                continue

        print(f"  => [{team_name}] собрано матчей: {taken}")
        return taken
    finally:
        await page.close()


async def run(
    leagues: List[str] | None = None,
    headless: bool | None = None,
    team_limit: int | None = None,
    matches_per_team: int | None = None,
    concurrency: int | None = None,
    out_csv: str | None = None,
):
    """Точка входа в пайплайн (параметры можно не указывать — будут взяты из config)."""
    leagues = leagues or config.LEAGUES
    headless = config.HEADLESS if headless is None else headless
    if team_limit is None:
        team_limit = config.TEAM_LIMIT
    matches_per_team = matches_per_team or config.MATCHES_PER_TEAM
    concurrency = concurrency or config.TEAMS_CONCURRENCY
    out_csv_path = config.OUT_CSV if out_csv is None else out_csv

    teams_agg: Dict[str, Dict] = {}
    agg_lock = asyncio.Lock()
    sem = asyncio.Semaphore(concurrency)

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/123.0.0.0 Safari/537.36"),
            locale="ru-RU",
            viewport={"width": 1400, "height": 900},
        )

        # Сначала собираем все команды по лигам
        league_page = await context.new_page()
        league_page.set_default_navigation_timeout(config.NAV_TIMEOUT_MS)
        league_page.set_default_timeout(config.DEF_TIMEOUT_MS)

        all_teams: List[Tuple[str, str]] = []
        for lid, league_url in enumerate(leagues, start=1):
            print(f"\n[LEAGUE {lid}/{len(leagues)}] {league_url}")
            teams = await get_team_links(league_page, league_url)
            print(f"[INFO] Найдено команд: {len(teams)}")
            if team_limit is not None:
                teams = teams[:team_limit]
                print(f"[INFO] Ограничение: берём первые {len(teams)} команд")
            all_teams.extend(teams)

        await league_page.close()

        # Параллельно обрабатываем команды
        async def team_task(team_name: str, team_link: str):
            async with sem:
                try:
                    await process_team(context, team_name, team_link, teams_agg, agg_lock)
                except Exception:
                    pass

        tasks = [asyncio.create_task(team_task(name, link)) for (name, link) in all_teams]
        await asyncio.gather(*tasks)

        await context.close()
        await browser.close()

    table = compute_sorted_table(teams_agg)
    write_averages_csv(table, out_csv_path)

    print(f"\n[OK] Готово. Итоговый CSV: {out_csv_path.resolve()}")
    if table:
        print("\nПолная таблица (все команды, отсортировано по среднему тоталу ↓):")
        for i, (name, avg_total, avg_team, avg_opp) in enumerate(table, start=1):
            print(f"{i:>2}. {name}: {avg_total:.2f} (инд: {avg_team:.2f}, соп: {avg_opp:.2f})")
