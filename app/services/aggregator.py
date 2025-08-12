"""
Агрегация и сохранение CSV.
"""
from typing import Dict, List, Tuple
import csv
from pathlib import Path


def update_team_agg(agg: Dict[str, Dict], team_name: str, team_corners: int, opp_corners: int):
    """Обновляем агрегаты команды (суммы и количество матчей)."""
    if team_name not in agg:
        agg[team_name] = {"cnt": 0, "sum_total": 0, "sum_team": 0, "sum_opp": 0}
    agg[team_name]["cnt"] += 1
    agg[team_name]["sum_total"] += (team_corners + opp_corners)
    agg[team_name]["sum_team"] += team_corners
    agg[team_name]["sum_opp"] += opp_corners


def compute_sorted_table(agg: Dict[str, Dict]) -> List[Tuple[str, float, float, float]]:
    """Считаем средние и сортируем по среднему тоталу (убыв.)."""
    rows: list[tuple[str, float, float, float]] = []
    for name, a in agg.items():
        if a["cnt"] == 0:
            continue
        avg_total = a["sum_total"] / a["cnt"]
        avg_team = a["sum_team"] / a["cnt"]
        avg_opp = a["sum_opp"] / a["cnt"]
        rows.append((name, avg_total, avg_team, avg_opp))
    rows.sort(key=lambda t: t[1], reverse=True)
    return rows


def write_averages_csv(rows: List[Tuple[str, float, float, float]], path: Path):
    """Сохраняем РОВНО в требуемом формате, без заголовка."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        for name, avg_total, avg_team, avg_opp in rows:
            w.writerow([name, f"{avg_total:.2f}", f"{avg_team:.2f}", f"{avg_opp:.2f}"])
