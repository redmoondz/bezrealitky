# Bezrealitky CSV parser

The parser reads every page of a Bezrealitky search, deduplicates publication
links, opens every publication, and writes the normalized data to CSV.

The `images` CSV cell contains a JSON array of ordered gallery URLs. Exact map
coordinates are stored separately in `latitude` and `longitude` (WGS84). These
values come from the same structured `gps` payload used by the site's MapLibre
marker. The `floor` cell (e.g. `"2. floor out of 2"`) is also split into numeric
`floor_number`/`floor_total` columns (`src/floor.py`), and `pets_friendly`
(`True`/`False`/empty-if-unknown) is classified from `description` by a small
Czech/English keyword taxonomy with typo-tolerant fuzzy matching (`src/pets.py`).

This CLI/CSV path (`src/cli.py`, `src/run_pipeline.py`) is kept for local,
offline, single-run use. For anything continuous or multi-user — a background
scheduler, a Postgres store, a Telegram bot — see **Postgres, the scheduler, and
the bot** below; that stack is the one meant to actually run day to day.

## Setup

```bash
python3 -m pip install -r requirements.txt
```

## Configure

Import a search URL and optionally override its price range:

```bash
python3 -m src.cli --url 'https://www.bezrealitky.com/search?estateType=BYT&offerType=PRONAJEM' --price_from 750 --price_to 1200
```

`--url` also accepts a Markdown link copied from a chat message. Only HTTPS
Bezrealitky `/search` URLs are accepted. Repeated query parameters such as
`disposition` are preserved.

Show the current config or restore the immutable defaults:

```bash
python3 -m src.cli --show
python3 -m src.cli --reset
```

The active settings live in `config/config.yaml`; defaults are kept separately
in `config/defaults.yaml`.

## Run

```bash
python3 -m src.run_pipeline
```

You can update the config and run immediately:

```bash
python3 -m src.cli --price_from 750 --price_to 1200 --run
```

The default output is `output/bezrealitky_listings.csv`. A non-zero exit code
means that one or more discovered publications could not be fetched or parsed;
successfully parsed rows are still saved.

## Docker

Build the image:

```bash
docker compose build
```

The container entrypoint is the same CLI. The Compose service mounts `config/`
and `output/`, so config updates and generated CSV files persist on the host:

```bash
docker compose run --rm scraper --show
docker compose run --rm scraper --price_from 750 --price_to 1200
docker compose run --rm scraper --url 'https://www.bezrealitky.com/search?estateType=BYT&offerType=PRONAJEM'
docker compose run --rm scraper --reset
docker compose run --rm scraper --run
```

Without Compose:

```bash
docker build -t bezrealitky-parser .
docker run --rm \
  -v "$PWD/config:/app/config" \
  -v "$PWD/output:/app/output" \
  bezrealitky-parser --run
```

## Postgres, the scheduler, and the bot

For continuous use, `docker compose` also runs:

- **`db`** — Postgres, the system of record. A shared, deduped cache of scraped
  ads (`listings`), plus per-Telegram-user state (`bot_users`,
  `user_listing_relevance`).
- **`translate`** — a self-hosted [LibreTranslate](https://libretranslate.com)
  instance (free, no API key) used to translate descriptions.
- **`scheduler`** — the same image as `scraper`, just started with a different
  entrypoint (`python -m src.scheduler`): every `SCRAPE_INTERVAL_HOURS` (default
  2), it re-runs **every registered Telegram user's own saved search** and syncs
  the results into Postgres.
- **`bot`** — a Telegram bot (aiogram) for browsing, remote-controlling the
  scraper, charts, and notifications. Built from `Dockerfile.bot` /
  `requirements-bot.txt`.

### Each user has their own saved search

There is no single shared "the current search" once the bot is involved — every
Telegram user gets their own independent saved search, stored as
`bot_users.search_url`. The first time a user runs `/parse` or `/parse_custom`,
it's seeded from the project's default (broad) search in `config/defaults.yaml`;
`/parse_custom` then edits *only that user's* search from then on. Two users can
have overlapping searches — the underlying ad data in `listings` is shared and
deduped by `listing_id` — but relevance and notifications are tracked per
`(user, listing)` pair in `user_listing_relevance`, never globally.

### `is_relevant` lifecycle

Every time a user's search is (re)run — scheduled or via `/parse`/`/parse_custom`
— that user's *entire* previous relevance for that ad set is flipped to
`is_relevant = FALSE`, then the search's live results are flipped back to `TRUE`.
So if a user narrows or changes their search, listings that no longer match just
stop being relevant (history preserved, not deleted); nothing needs to detect
*that* the config changed — relevance is always recomputed from the live result.

### Setup

```bash
cp .env.example .env
# fill in TELEGRAM_BOT_API (from @BotFather), TELEGRAM_ALLOWED_USER_IDS (your
# Telegram user ID, e.g. from @userinfobot), and a POSTGRES_PASSWORD.

docker compose up -d db translate
docker compose build scraper bot

# One-time: import the legacy CSV into the shared `listings` cache.
docker compose run --rm --entrypoint python3 scraper -m src.migrate --csv output/bezrealitky_listings.csv

docker compose up -d scheduler bot
```

`TELEGRAM_ALLOWED_USER_IDS` gates every command except `/start`/`/language`
(picking a language is harmless) — it **fails closed**: leave it empty and the
bot refuses every gated command with a setup hint instead of defaulting open.

### Bot commands

| Command | What it does |
|---|---|
| `/start`, `/language` | Pick the language listing descriptions get translated into |
| `/list` | Paginate your saved search's matching listings (photo, price, area, floor, pets, link) |
| `/view <listing_id>` | Full detail + all photos for one listing |
| `/search` | Show your current saved search URL |
| `/parse` | Run the scraper now with your saved search |
| `/parse_custom <flags>` | Update *your* saved search with CLI-style flags and run it now |
| `/parse_help` | The exact accepted flags for `/parse_custom` (generated from the real CLI parser, so it can't drift) |
| `/charts` | Area/price/price-per-m² distributions, price-vs-area, and layout/pets_friendly breakdowns for your saved search |

New listings that become relevant to a user's saved search are pushed to them
automatically (their own Telegram chat) — checked every `NOTIFY_POLL_SECONDS`
(default 10 min) by the bot process, independent of the scheduler's own 2-hour
cadence.
