"""
Утилиты: небольшие функции общего назначения.
"""
import asyncio
import random
import re
from urllib.parse import urlparse

# Задержки (мс) для человекоподобного поведения
DELAY_MIN_MS = 120
DELAY_MAX_MS = 280


async def tiny_sleep():
    """Случайная короткая пауза между действиями."""
    await asyncio.sleep(random.uniform(DELAY_MIN_MS / 1000, DELAY_MAX_MS / 1000))


def normalize_match_stats_url(href: str) -> str:
    """Нормализуем ссылку так, чтобы открывалась вкладка статистики."""
    if "#/match-summary/match-statistics/0" in href:
        return href
    base = href.split("#/match-summary")[0].rstrip("/")
    return base + "/#/match-summary/match-statistics/0"


def extract_match_id(url: str):
    """Достаём ID матча из URL (после /match/football/...)."""
    try:
        parts = urlparse(url).path.strip("/").split("/")
        if "match" in parts and "football" in parts:
            i = parts.index("football")
            return parts[i + 1]
    except Exception:
        return None
    return None


def to_int_safe(s: str):
    """Преобразуем строку в int, вытаскивая первые цифры."""
    if not s:
        return None
    m = re.search(r"\d+", s.replace("\xa0", " ").strip())
    return int(m.group()) if m else None


def clean_team_name(name: str | None) -> str | None:
    """Убираем хвост со счётом и лишние пробелы/дефисы."""
    if not name:
        return name
    n = re.sub(r"\s+\d+\s*[:–-]\s*\d+\s*$", "", name)
    n = re.sub(r"\s+", " ", n).strip(" -–—\u00a0")
    return n or None


def norm_for_compare(name: str) -> str:
    """Нормализация имени для сравнения (нижний регистр, сжатые пробелы, без мусора)."""
    n = name.lower()
    n = n.replace("ё", "е")
    n = re.sub(r"[^a-zа-я0-9]+", " ", n)
    n = re.sub(r"\bфк\b", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n
