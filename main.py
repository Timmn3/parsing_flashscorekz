"""
Запуск проекта.
Примеры:
    python main.py
    python main.py --headless 1 --teams-limit 5 --matches 10 --concurrency 5 --csv out.csv
    python main.py   --leagues "https://www.flashscorekz.com/football/england/premier-league-2024-2025/standings/#/lAkHuyP3/table/overall,https://www.flashscorekz.com/football/spain/laliga-2024-2025/#/dINOZk9Q/table/overall"
"""
import argparse
import asyncio
from app.services.pipeline import run

def parse_args():
    p = argparse.ArgumentParser(description="Парсер угловых (последние N матчей) для команд из нескольких лиг Flashscore + CSV.")
    p.add_argument("--leagues", type=str, help="Список URL лиг через запятую.")
    p.add_argument("--headless", type=int, choices=[0,1], help="Запуск браузера без интерфейса (0/1).")
    p.add_argument("--teams-limit", type=int, help="Ограничение на количество команд в каждой лиге.")
    p.add_argument("--matches", type=int, help="Сколько последних матчей на команду брать.")
    p.add_argument("--concurrency", type=int, help="Сколько команд обрабатывать параллельно.")
    p.add_argument("--csv", type=str, help="Путь к выходному CSV.")
    return p.parse_args()

def main():
    args = parse_args()
    leagues = args.leagues.split(",") if args.leagues else None
    headless = None if args.headless is None else bool(args.headless)
    asyncio.run(run(
        leagues=leagues,
        headless=headless,
        team_limit=args.teams_limit,
        matches_per_team=args.matches,
        concurrency=args.concurrency,
        out_csv=args.csv,
    ))

if __name__ == "__main__":
    main()
