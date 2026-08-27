"""Postgres schema, connection, and upsert logic for scraped listings.

Each Telegram user has their own independent saved search (``bot_users.search_url``),
so relevance/notification state can't live on ``listings`` itself — a listing can be
relevant to one user's search and not another's. ``listings`` is a shared, deduped
cache of scraped ad data (keyed by ``listing_id``); ``user_listing_relevance`` tracks,
per ``(telegram_user_id, listing_id)`` pair, whether that user's *current* search
still matches it and whether they've been notified about it.

Uses the synchronous ``psycopg`` (v3) driver everywhere: the scheduler calls it
directly, and the (async) Telegram bot wraps calls in ``asyncio.to_thread`` rather
than pulling in a second, async-only driver.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from typing import Iterable

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg.types.json import Json

try:
    from .scraper import Listing
except ImportError:  # Support: python3 src/db.py
    from scraper import Listing  # type: ignore[no-redef]

LOGGER = logging.getLogger(__name__)

load_dotenv()

# Columns that are copied verbatim from Listing as text; everything else needs a
# type conversion (numeric/boolean/json) handled in row_from_listing.
_TEXT_COLUMNS = (
    "listing_id",
    "name",
    "format",
    "currency",
    "url",
    "available_from",
    "location",
    "description",
    "heating",
    "floor",
    "fully_furnished",
)

_NUMERIC_COLUMNS = (
    "area",
    "total_price",
    "monthly_rent",
    "refundable_deposit",
    "service_charges",
    "utility_charges",
    "price_per_unit",
    "latitude",
    "longitude",
)

_INTEGER_COLUMNS = ("floor_number", "floor_total")

_ALL_COLUMNS = _TEXT_COLUMNS + _NUMERIC_COLUMNS + _INTEGER_COLUMNS + ("images", "pets_friendly")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS listings (
    listing_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    format TEXT NOT NULL DEFAULT '',
    area NUMERIC,
    total_price NUMERIC,
    currency TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    images JSONB NOT NULL DEFAULT '[]',
    available_from TEXT NOT NULL DEFAULT '',
    monthly_rent NUMERIC,
    refundable_deposit NUMERIC,
    service_charges NUMERIC,
    utility_charges NUMERIC,
    price_per_unit NUMERIC,
    location TEXT NOT NULL DEFAULT '',
    latitude NUMERIC,
    longitude NUMERIC,
    description TEXT NOT NULL DEFAULT '',
    heating TEXT NOT NULL DEFAULT '',
    floor TEXT NOT NULL DEFAULT '',
    floor_number INTEGER,
    floor_total INTEGER,
    fully_furnished TEXT NOT NULL DEFAULT '',
    pets_friendly BOOLEAN,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bot_users (
    telegram_user_id BIGINT PRIMARY KEY,
    language_code TEXT NOT NULL DEFAULT 'en',
    search_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_listing_relevance (
    telegram_user_id BIGINT NOT NULL REFERENCES bot_users (telegram_user_id) ON DELETE CASCADE,
    listing_id TEXT NOT NULL REFERENCES listings (listing_id) ON DELETE CASCADE,
    is_relevant BOOLEAN NOT NULL DEFAULT TRUE,
    notified_at TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (telegram_user_id, listing_id)
);
CREATE INDEX IF NOT EXISTS user_listing_relevance_relevant_idx
    ON user_listing_relevance (telegram_user_id, is_relevant);
"""

_LISTINGS_UPSERT_SQL = f"""
INSERT INTO listings ({", ".join(_ALL_COLUMNS)}, last_seen_at)
VALUES ({", ".join(f"%({column})s" for column in _ALL_COLUMNS)}, now())
ON CONFLICT (listing_id) DO UPDATE SET
    {", ".join(f"{column} = EXCLUDED.{column}" for column in _ALL_COLUMNS if column != "listing_id")},
    last_seen_at = now()
"""

_RELEVANCE_UPSERT_SQL = """
INSERT INTO user_listing_relevance (telegram_user_id, listing_id, is_relevant, last_seen_at)
VALUES (%(telegram_user_id)s, %(listing_id)s, TRUE, now())
ON CONFLICT (telegram_user_id, listing_id) DO UPDATE SET
    is_relevant = TRUE,
    last_seen_at = now()
"""

_RELEVANT_JOIN_SQL = """
SELECT l.* FROM listings l
JOIN user_listing_relevance r ON r.listing_id = l.listing_id
WHERE r.telegram_user_id = %s AND r.is_relevant
"""


def get_dsn() -> str:
    return (
        f"host={os.environ.get('POSTGRES_HOST', 'db')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'bezrealitky')} "
        f"user={os.environ.get('POSTGRES_USER', 'bezrealitky')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', '')}"
    )


def connect() -> psycopg.Connection:
    # autocommit=True so a bare read (get_user_search, list_registered_users, ...)
    # never leaves an implicit transaction open on the connection — otherwise a
    # later `with conn.transaction():` nests as a savepoint inside it instead of
    # a real commit, and the write silently vanishes if the connection later
    # closes without an explicit top-level commit. This is psycopg3's own
    # recommended pattern: autocommit on, explicit `transaction()` blocks only
    # for the operations that truly need multi-statement atomicity.
    return psycopg.connect(get_dsn(), row_factory=dict_row, autocommit=True)


def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute(SCHEMA_SQL)
    conn.commit()


def _decimal_or_none(value: str) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _int_or_none(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _bool_or_none(value: str) -> bool | None:
    if value == "True":
        return True
    if value == "False":
        return False
    return None


def row_from_listing(listing: Listing) -> dict:
    """Convert a :class:`Listing`'s string fields into typed DB parameters."""
    data = asdict(listing)
    row: dict = {column: data[column] for column in _TEXT_COLUMNS}
    for column in _NUMERIC_COLUMNS:
        row[column] = _decimal_or_none(data[column])
    for column in _INTEGER_COLUMNS:
        row[column] = _int_or_none(data[column])
    try:
        images = json.loads(data["images"]) if data["images"] else []
    except json.JSONDecodeError:
        images = []
    row["images"] = Json(images)
    row["pets_friendly"] = _bool_or_none(data["pets_friendly"])
    return row


def ensure_bot_user(conn: psycopg.Connection, telegram_user_id: int) -> None:
    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO bot_users (telegram_user_id) VALUES (%s) "
                "ON CONFLICT (telegram_user_id) DO NOTHING",
                (telegram_user_id,),
            )


def sync_user_listings(
    conn: psycopg.Connection, telegram_user_id: int, listings: Iterable[Listing]
) -> dict:
    """Upsert one user's scrape run and flip their stale matches to ``is_relevant = FALSE``.

    ``listings`` (the shared ad cache) is upserted first, then every row this run
    did not (re)discover for this user keeps its history but stops being
    ``is_relevant`` for *them* — other users' relevance is untouched. This is the
    entire "saved search changed" lifecycle: a user's relevance is always
    recomputed from their current search's live results, never diffed.
    """
    ensure_bot_user(conn, telegram_user_id)
    rows = [row_from_listing(listing) for listing in listings]
    with conn.transaction():
        with conn.cursor() as cursor:
            for row in rows:
                cursor.execute(_LISTINGS_UPSERT_SQL, row)
            cursor.execute(
                "UPDATE user_listing_relevance SET is_relevant = FALSE WHERE telegram_user_id = %s",
                (telegram_user_id,),
            )
            for row in rows:
                cursor.execute(
                    _RELEVANCE_UPSERT_SQL,
                    {"telegram_user_id": telegram_user_id, "listing_id": row["listing_id"]},
                )
    LOGGER.info("Synced %d listings for user %s (now relevant)", len(rows), telegram_user_id)
    return {"synced": len(rows)}


def import_listings(conn: psycopg.Connection, listings: Iterable[Listing]) -> int:
    """Bulk-load listings (e.g. from the legacy CSV) into the shared cache only —
    a one-time historical backfill with no associated user, so it touches no
    relevance state. Each user's next scheduled sync populates their own.
    """
    rows = [row_from_listing(listing) for listing in listings]
    with conn.transaction():
        with conn.cursor() as cursor:
            for row in rows:
                cursor.execute(_LISTINGS_UPSERT_SQL, row)
    return len(rows)


def fetch_relevant_listings(conn: psycopg.Connection, telegram_user_id: int) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(_RELEVANT_JOIN_SQL + " ORDER BY r.last_seen_at DESC", (telegram_user_id,))
        return cursor.fetchall()


def count_relevant_listings(conn: psycopg.Connection, telegram_user_id: int) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) AS n FROM user_listing_relevance "
            "WHERE telegram_user_id = %s AND is_relevant",
            (telegram_user_id,),
        )
        return cursor.fetchone()["n"]


def fetch_relevant_listings_page(
    conn: psycopg.Connection, telegram_user_id: int, offset: int, limit: int
) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            _RELEVANT_JOIN_SQL + " ORDER BY r.last_seen_at DESC, l.listing_id DESC OFFSET %s LIMIT %s",
            (telegram_user_id, offset, limit),
        )
        return cursor.fetchall()


def fetch_unnotified_relevant_listings(conn: psycopg.Connection, telegram_user_id: int) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            _RELEVANT_JOIN_SQL + " AND r.notified_at IS NULL ORDER BY r.first_seen_at ASC",
            (telegram_user_id,),
        )
        return cursor.fetchall()


def mark_notified(conn: psycopg.Connection, telegram_user_id: int, listing_ids: Iterable[str]) -> None:
    ids = list(listing_ids)
    if not ids:
        return
    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE user_listing_relevance SET notified_at = now() "
                "WHERE telegram_user_id = %s AND listing_id = ANY(%s)",
                (telegram_user_id, ids),
            )


def fetch_listing(conn: psycopg.Connection, listing_id: str) -> dict | None:
    """Look up one listing regardless of whose search it currently matches — the
    underlying ad data is shared, only "is this relevant right now" is per-user.
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM listings WHERE listing_id = %s", (listing_id,))
        return cursor.fetchone()


DEFAULT_LANGUAGE = "en"


def get_user_language(conn: psycopg.Connection, telegram_user_id: int) -> str:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT language_code FROM bot_users WHERE telegram_user_id = %s",
            (telegram_user_id,),
        )
        row = cursor.fetchone()
        return row["language_code"] if row else DEFAULT_LANGUAGE


def set_user_language(conn: psycopg.Connection, telegram_user_id: int, language_code: str) -> None:
    ensure_bot_user(conn, telegram_user_id)
    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE bot_users SET language_code = %s, updated_at = now() "
                "WHERE telegram_user_id = %s",
                (language_code, telegram_user_id),
            )


def get_user_search(conn: psycopg.Connection, telegram_user_id: int) -> str | None:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT search_url FROM bot_users WHERE telegram_user_id = %s",
            (telegram_user_id,),
        )
        row = cursor.fetchone()
        return row["search_url"] if row else None


def set_user_search(conn: psycopg.Connection, telegram_user_id: int, search_url: str) -> None:
    ensure_bot_user(conn, telegram_user_id)
    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE bot_users SET search_url = %s, updated_at = now() "
                "WHERE telegram_user_id = %s",
                (search_url, telegram_user_id),
            )


def get_or_seed_user_search(conn: psycopg.Connection, telegram_user_id: int, default_url: str) -> str:
    """Return the user's saved search, creating one from ``default_url`` on first use."""
    ensure_bot_user(conn, telegram_user_id)
    existing = get_user_search(conn, telegram_user_id)
    if existing:
        return existing
    set_user_search(conn, telegram_user_id, default_url)
    return default_url


def list_registered_users(conn: psycopg.Connection) -> list[int]:
    """Every Telegram user who has an active saved search (i.e. has used /parse
    or /parse_custom at least once) — what the scheduler and notify loop iterate.
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT telegram_user_id FROM bot_users WHERE search_url IS NOT NULL")
        return [row["telegram_user_id"] for row in cursor.fetchall()]
