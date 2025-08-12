from pathlib import Path
import os
import re

# -------------------- Значения по умолчанию --------------------
_DEFAULT_LEAGUES = [
    "https://www.flashscorekz.com/football/england/premier-league-2024-2025/standings/#/lAkHuyP3/table/overall",
    "https://www.flashscorekz.com/football/spain/laliga-2024-2025/#/dINOZk9Q/table/overall",
]
BASE_URL = "https://www.flashscorekz.com/"

# -------------------- Вспомогательные парсеры --------------------
_TRUE_SET = {"1", "true", "True", "YES", "yes", "y", "on"}

def _env_bool(name: str, default: bool) -> bool:
    """Парсинг булевого значения из ENV."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip() in _TRUE_SET

def _env_int(name: str, default: int) -> int:
    """Парсинг целого значения из ENV."""
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default

def _env_str(name: str, default: str) -> str:
    """Парсинг строки из ENV."""
    raw = os.getenv(name)
    return default if raw is None else str(raw)

def _env_leagues(name: str, default_list: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return default_list

    parts = re.split(r"[,\n;]+", raw)
    leagues = [p.strip() for p in parts if p.strip()]
    return leagues or default_list

# -------------------- Параметры из ENV --------------------
HEADLESS = _env_bool("HEADLESS", False)

TEAM_LIMIT = _env_int("TEAM_LIMIT", 0) or None   # None = без ограничения
MATCHES_PER_TEAM = _env_int("MATCHES_PER_TEAM", 10)
TEAMS_CONCURRENCY = _env_int("TEAMS_CONCURRENCY", 5)

# Таймауты (мс)
NAV_TIMEOUT_MS = _env_int("NAV_TIMEOUT_MS", 8000)
DEF_TIMEOUT_MS = _env_int("DEF_TIMEOUT_MS", 8000)
COOKIE_BTN_TIMEOUT_MS = _env_int("COOKIE_BTN_TIMEOUT_MS", 1000)
WAIT_EVENTLINKS_TIMEOUT_MS = _env_int("WAIT_EVENTLINKS_TIMEOUT_MS", 8000)
STAT_ROW_TIMEOUT_MS = _env_int("STAT_ROW_TIMEOUT_MS", 10000)

# Флаги
FORCE_SCROLL_STATS = _env_bool("FORCE_SCROLL_STATS", True)

# Список лиг
LEAGUES = _env_leagues("LEAGUES", _DEFAULT_LEAGUES)

# Файл результата
OUT_CSV = Path(_env_str("OUT_CSV", "OUT/teams_corners.csv"))
