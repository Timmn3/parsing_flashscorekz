# Flashscore Corners — асинхронный парсер угловых (Playwright)

Инструмент для сбора статистики **угловых** по последним матчам команд из выбранных лиг на Flashscore и расчёта средних значений по каждой команде с сохранением в CSV.

- Собирает список команд со страниц лиг.
- Переходит в карточку команды → вкладка «Последние результаты».
- Открывает матчи (до `N` на команду), парсит строку «Угловые».
- Агрегирует и сортирует команды по **среднему тоталу угловых**, записывает CSV.

> Реализовано на Python 3.12 + Playwright (async). Перед первым запуском обязательно выполните `playwright install`.

---

## Требования

- **Python**: 3.12+
- **Зависимости**: `playwright` (см. `requirements.txt`)
- **Браузеры Playwright**: установить через `playwright install`

---

## Установка

```bash
# 1) создать виртуальное окружение
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2) зависимости
pip install -r requirements.txt

# 3) установить браузеры Playwright
playwright install
```

---

## Быстрый старт

### Вариант A: запуск с настройками по умолчанию (ENV + значения по умолчанию)
```bash
python main.py
```

### Вариант B: запуск с параметрами из CLI
```bash
# headless-режим, ограничить по 5 команд на лигу, взять по 10 матчей, параллельность 5, свой путь CSV
python main.py --headless 1 --teams-limit 5 --matches 10 --concurrency 5 --csv OUT/teams_corners.csv
```

### Вариант C: свои лиги (через запятую)
```bash
python main.py   --leagues "https://www.flashscorekz.com/football/england/premier-league-2024-2025/standings/#/lAkHuyP3/table/overall,https://www.flashscorekz.com/football/spain/laliga-2024-2025/#/dINOZk9Q/table/overall"
```

---

## Конфигурация

Настройки можно задавать через **переменные окружения** (.env) или CLI. Значения по умолчанию определены в коде.

Поддерживаемые переменные окружения:

- `HEADLESS` — `1` без интерфейса / `0` с интерфейсом (по умолчанию: `1`).
- `TEAM_LIMIT` — макс. число команд на лигу (`0` или пусто = без ограничения).
- `MATCHES_PER_TEAM` — сколько матчей брать на команду (по умолчанию `10`).
- `TEAMS_CONCURRENCY` — параллельная обработка команд (по умолчанию `5`).

**Таймауты (мс):**  
`NAV_TIMEOUT_MS`, `DEF_TIMEOUT_MS`, `COOKIE_BTN_TIMEOUT_MS`, `WAIT_EVENTLINKS_TIMEOUT_MS`, `STAT_ROW_TIMEOUT_MS`.

- `FORCE_SCROLL_STATS` — прокрутка блока статистики, если «Угловые» не видны сразу (0/1).
- `LEAGUES` — список URL лиг (через запятую **или** многострочно).
- `OUT_CSV` — путь к результирующему CSV (по умолчанию `OUT/teams_corners.csv`).

Пример `.env`:
```dotenv
# 0 = с интерфейсом, 1 = headless
HEADLESS=1
TEAM_LIMIT=0
MATCHES_PER_TEAM=10
TEAMS_CONCURRENCY=5

NAV_TIMEOUT_MS=8000
DEF_TIMEOUT_MS=8000
COOKIE_BTN_TIMEOUT_MS=1000
WAIT_EVENTLINKS_TIMEOUT_MS=8000
STAT_ROW_TIMEOUT_MS=10000

FORCE_SCROLL_STATS=1

OUT_CSV=OUT/teams_corners.csv

LEAGUES="
https://www.flashscorekz.com/football/england/premier-league-2024-2025/standings/#/lAkHuyP3/table/overall
https://www.flashscorekz.com/football/spain/laliga-2024-2025/#/dINOZk9Q/table/overall
"
```

---

## Формат результата (CSV)

Без заголовка, **ровно 4 колонки** в таком порядке:

```
<название команды>,<средний тотал угловых>,<средний ИТТ команды>,<средний ИТТ соперников>
```

Числа сохраняются с **двумя знаками** после запятой (пример: `9.80,5.10,4.70`).

---

## Как это работает

1. Для каждой лиги собираются ссылки команд.
2. Для каждой команды открывается вкладка **«Последние результаты»**, берутся ссылки матчей и переходы на страницу **Статистика → Угловые**.
3. Парсятся значения угловых с учётом разных вариантов вёрстки Flashscore (новая/старая) и возможной прокрутки.
4. Сопоставляются данные по команде (дом/гости), считаются суммы и средние.
5. Результат записывается в CSV по пути `OUT_CSV`.

---

## Архитектура проекта

```
.
├── app
│   ├── config.py              # значения по умолчанию + парсинг ENV
│   ├── utils.py               # утилиты (нормализация URL/имён, задержки)
│   ├── scraper
│   │   ├── navigation.py      # переходы и ожидания стабильности DOM
│   │   ├── teams_extractor.py # сбор ссылок команд со страниц лиг
│   │   └── match_parser.py    # парсинг вкладки статистики «Угловые»
│   └── services
│       ├── aggregator.py      # агрегация и запись CSV
│       └── pipeline.py        # основной асинхронный пайплайн
├── OUT/
│   └── teams_corners.csv      # результирующий CSV (создаётся при запуске)
├── main.py                    # точка входа и CLI-параметры
├── requirements.txt
└── README.md
```
