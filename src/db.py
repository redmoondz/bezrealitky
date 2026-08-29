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
    from .scoring import compute_score
    from .scraper import Listing
    from .translate import translate_description
except ImportError:  # Support: python3 src/db.py
    from scoring import compute_score  # type: ignore[no-redef]
    from scraper import Listing  # type: ignore[no-redef]
    from translate import translate_description  # type: ignore[no-redef]

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
    "construction",
    "condition",
    "surroundings",
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

_BOOLEAN_COLUMNS = (
    "pets_friendly",
    "air_conditioning",
    "has_washing_machine",
    "has_dryer",
    "has_internet",
    "has_dishwasher",
    "mansard",
    "balcony",
    "oven",
    "microwave",
    "refrigerator",
    "quiet_surroundings",
    "garage",
    "english_speaking",
)

_ALL_COLUMNS = _TEXT_COLUMNS + _NUMERIC_COLUMNS + _INTEGER_COLUMNS + ("images", "tags") + _BOOLEAN_COLUMNS

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
    construction TEXT NOT NULL DEFAULT '',
    condition TEXT NOT NULL DEFAULT '',
    surroundings TEXT NOT NULL DEFAULT '',
    pets_friendly BOOLEAN,
    air_conditioning BOOLEAN,
    has_washing_machine BOOLEAN,
    has_dryer BOOLEAN,
    has_internet BOOLEAN,
    has_dishwasher BOOLEAN,
    mansard BOOLEAN,
    balcony BOOLEAN,
    oven BOOLEAN,
    microwave BOOLEAN,
    refrigerator BOOLEAN,
    quiet_surroundings BOOLEAN,
    garage BOOLEAN,
    english_speaking BOOLEAN,
    -- Every _BOOLEAN_COLUMNS entry that's True, by name — one place analytics
    -- can query tag frequency/combinations without scanning 13 columns, e.g.
    -- SELECT jsonb_array_elements_text(tags), count(*) FROM listings GROUP BY 1.
    tags JSONB NOT NULL DEFAULT '[]',
    -- {language_code: translated_text}. Populated once per (listing, language) —
    -- by sync_user_listings for whoever's search just found it, and lazily by
    -- get_or_translate_description for any other language a viewer needs —
    -- and never re-translated after that, since the shared cache means every
    -- other user (or repeat view) in that language reads it back for free.
    description_translations JSONB NOT NULL DEFAULT '{}',
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- listings existed before these columns were added; CREATE TABLE IF NOT EXISTS
-- above is a no-op against an already-deployed table, so new columns need an
-- explicit, idempotent ALTER here to reach a running database.
ALTER TABLE listings ADD COLUMN IF NOT EXISTS construction TEXT NOT NULL DEFAULT '';
ALTER TABLE listings ADD COLUMN IF NOT EXISTS condition TEXT NOT NULL DEFAULT '';
ALTER TABLE listings ADD COLUMN IF NOT EXISTS surroundings TEXT NOT NULL DEFAULT '';
ALTER TABLE listings ADD COLUMN IF NOT EXISTS air_conditioning BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS has_washing_machine BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS has_dryer BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS has_internet BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS has_dishwasher BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS mansard BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS balcony BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS oven BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS microwave BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS refrigerator BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS quiet_surroundings BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS garage BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS english_speaking BOOLEAN;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]';
ALTER TABLE listings ADD COLUMN IF NOT EXISTS description_translations JSONB NOT NULL DEFAULT '{}';

-- Every Telegram account that has ever messaged the bot (recorded by a
-- dispatcher-wide middleware on first contact) — independent of ``bot_users``,
-- which only tracks people who've actually engaged with the bot's own
-- features (a saved search, a language choice). This is Telegram's own
-- profile info, not anything the person configures in the bot.
CREATE TABLE IF NOT EXISTS users (
    telegram_user_id BIGINT PRIMARY KEY,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    telegram_language_code TEXT NOT NULL DEFAULT '',
    is_premium BOOLEAN NOT NULL DEFAULT FALSE,
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

-- One row per user, collected during onboarding; every column is nullable
-- because every onboarding question is skippable, and a skip must mean "no
-- preference" (score always neutral), not an assumed value.
CREATE TABLE IF NOT EXISTS user_preferences (
    telegram_user_id BIGINT PRIMARY KEY REFERENCES bot_users (telegram_user_id) ON DELETE CASCADE,
    wants_pets BOOLEAN,
    budget_total_price NUMERIC,
    min_area_m2 NUMERIC,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_listing_relevance (
    telegram_user_id BIGINT NOT NULL REFERENCES bot_users (telegram_user_id) ON DELETE CASCADE,
    listing_id TEXT NOT NULL REFERENCES listings (listing_id) ON DELETE CASCADE,
    is_relevant BOOLEAN NOT NULL DEFAULT TRUE,
    score INTEGER NOT NULL DEFAULT 0,
    notified_at TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (telegram_user_id, listing_id)
);
CREATE INDEX IF NOT EXISTS user_listing_relevance_relevant_idx
    ON user_listing_relevance (telegram_user_id, is_relevant);

-- user_listing_relevance existed before scoring — see the ALTER block above
-- listings for why this needs an explicit, idempotent ALTER too.
ALTER TABLE user_listing_relevance ADD COLUMN IF NOT EXISTS score INTEGER NOT NULL DEFAULT 0;

-- 'like' / 'dislike' / NULL (not yet reacted to). Written only by
-- record_reaction(), never touched by sync_user_listings()'s relevance
-- reset -- same survives-a-resync guarantee notified_at already has.
ALTER TABLE user_listing_relevance ADD COLUMN IF NOT EXISTS reaction TEXT;
ALTER TABLE user_listing_relevance ADD COLUMN IF NOT EXISTS reacted_at TIMESTAMPTZ;
"""

_LISTINGS_UPSERT_SQL = f"""
INSERT INTO listings ({", ".join(_ALL_COLUMNS)}, last_seen_at)
VALUES ({", ".join(f"%({column})s" for column in _ALL_COLUMNS)}, now())
ON CONFLICT (listing_id) DO UPDATE SET
    {", ".join(f"{column} = EXCLUDED.{column}" for column in _ALL_COLUMNS if column != "listing_id")},
    last_seen_at = now()
"""

_RELEVANCE_UPSERT_SQL = """
INSERT INTO user_listing_relevance (telegram_user_id, listing_id, is_relevant, score, last_seen_at)
VALUES (%(telegram_user_id)s, %(listing_id)s, TRUE, %(score)s, now())
ON CONFLICT (telegram_user_id, listing_id) DO UPDATE SET
    is_relevant = TRUE,
    score = EXCLUDED.score,
    last_seen_at = now()
"""

_RELEVANT_JOIN_SQL = """
SELECT l.*, r.score FROM listings l
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
    for column in _BOOLEAN_COLUMNS:
        row[column] = _bool_or_none(data[column])
    row["tags"] = Json([column for column in _BOOLEAN_COLUMNS if row[column] is True])
    return row


def upsert_telegram_user(
    conn: psycopg.Connection,
    telegram_user_id: int,
    first_name: str,
    last_name: str,
    username: str,
    telegram_language_code: str,
    is_premium: bool,
) -> None:
    """Record (or refresh) one Telegram account's profile snapshot — called by
    the bot's tracking middleware on every incoming message/callback, so a
    name or username change is picked up too, not just the first contact.
    """
    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (telegram_user_id, first_name, last_name, username,
                    telegram_language_code, is_premium)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (telegram_user_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    username = EXCLUDED.username,
                    telegram_language_code = EXCLUDED.telegram_language_code,
                    is_premium = EXCLUDED.is_premium,
                    last_seen_at = now()
                """,
                (telegram_user_id, first_name, last_name, username, telegram_language_code, is_premium),
            )


def ensure_bot_user(conn: psycopg.Connection, telegram_user_id: int) -> None:
    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO bot_users (telegram_user_id) VALUES (%s) "
                "ON CONFLICT (telegram_user_id) DO NOTHING",
                (telegram_user_id,),
            )


def get_or_translate_description(
    conn: psycopg.Connection, listing_id: str, description: str, language: str
) -> tuple[str, bool]:
    """Read this listing's cached translation for ``language``; translate and
    persist it if it isn't cached yet. Returns ``(text_to_show, translation_ok)``
    exactly like :func:`src.translate.translate_description` — once a language
    is cached for a listing, every later view (any user, any number of times)
    is a plain cache read, never another network call.
    """
    if not description:
        return description, True
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT description_translations FROM listings WHERE listing_id = %s", (listing_id,)
        )
        row = cursor.fetchone()
    translations = dict(row["description_translations"]) if row and row["description_translations"] else {}
    cached = translations.get(language)
    # A cached value identical to the raw source isn't a real translation — most
    # likely a stale result from a since-fixed language-detection bug (see
    # src/translate.py) — so treat it as a miss and retry instead of serving a
    # known-untranslated description forever.
    if cached and cached != description:
        return cached, True
    translated, ok = translate_description(description, language)
    if ok:
        translations[language] = translated
        with conn.transaction():
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE listings SET description_translations = %s WHERE listing_id = %s",
                    (Json(translations), listing_id),
                )
    return translated, ok


def sync_user_listings(
    conn: psycopg.Connection, telegram_user_id: int, listings: Iterable[Listing]
) -> dict:
    """Upsert one user's scrape run and flip their stale matches to ``is_relevant = FALSE``.

    ``listings`` (the shared ad cache) is upserted first, then every row this run
    did not (re)discover for this user keeps its history but stops being
    ``is_relevant`` for *them* — other users' relevance is untouched. This is the
    entire "saved search changed" lifecycle: a user's relevance is always
    recomputed from their current search's live results, never diffed.

    Every newly-synced listing's description is also translated into this
    user's own language and cached (see :func:`get_or_translate_description`)
    before this function returns — translation happens up front, at sync time,
    not the first time someone happens to view the listing.
    """
    ensure_bot_user(conn, telegram_user_id)
    language = get_user_language(conn, telegram_user_id)
    rows = [row_from_listing(listing) for listing in listings]
    preferences = get_user_preferences(conn, telegram_user_id)
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
                    {
                        "telegram_user_id": telegram_user_id,
                        "listing_id": row["listing_id"],
                        "score": compute_score(row, preferences),
                    },
                )
    for row in rows:
        get_or_translate_description(conn, row["listing_id"], row["description"], language)
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
        cursor.execute(
            _RELEVANT_JOIN_SQL + " ORDER BY r.score DESC, r.last_seen_at DESC", (telegram_user_id,)
        )
        return cursor.fetchall()


def count_relevant_listings(conn: psycopg.Connection, telegram_user_id: int) -> int:
    """Count of the /list swipe queue — relevant listings not yet reacted to.

    Reacted listings are excluded here (unlike :func:`fetch_relevant_listings`,
    used for /charts) since once a user likes or dislikes a listing it's
    "seen" and shouldn't keep occupying their queue.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) AS n FROM user_listing_relevance "
            "WHERE telegram_user_id = %s AND is_relevant AND reaction IS NULL",
            (telegram_user_id,),
        )
        return cursor.fetchone()["n"]


def fetch_relevant_listings_page(
    conn: psycopg.Connection, telegram_user_id: int, offset: int, limit: int
) -> list[dict]:
    """One page of the /list swipe queue — see :func:`count_relevant_listings`
    for why reacted listings are excluded.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            _RELEVANT_JOIN_SQL
            + " AND r.reaction IS NULL"
            + " ORDER BY r.score DESC, r.last_seen_at DESC, l.listing_id DESC OFFSET %s LIMIT %s",
            (telegram_user_id, offset, limit),
        )
        return cursor.fetchall()


def count_liked_listings(conn: psycopg.Connection, telegram_user_id: int) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) AS n FROM user_listing_relevance "
            "WHERE telegram_user_id = %s AND reaction = 'like'",
            (telegram_user_id,),
        )
        return cursor.fetchone()["n"]


def fetch_liked_listings_page(
    conn: psycopg.Connection, telegram_user_id: int, offset: int, limit: int
) -> list[dict]:
    """One page of a user's personal liked-listings list, most recently liked
    first. Filtered on ``reaction = 'like'`` rather than ``is_relevant`` — a
    liked listing stays in this list even if a later resync or saved-search
    change would otherwise drop it from /list.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT l.*, r.score FROM listings l "
            "JOIN user_listing_relevance r ON r.listing_id = l.listing_id "
            "WHERE r.telegram_user_id = %s AND r.reaction = 'like' "
            "ORDER BY r.reacted_at DESC OFFSET %s LIMIT %s",
            (telegram_user_id, offset, limit),
        )
        return cursor.fetchall()


def record_reaction(
    conn: psycopg.Connection, telegram_user_id: int, listing_id: str, reaction: str
) -> None:
    """Record a like/dislike. A plain UPDATE, not an upsert — the row already
    exists because the listing was loaded via a query joining this same table.
    """
    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE user_listing_relevance SET reaction = %s, reacted_at = now() "
                "WHERE telegram_user_id = %s AND listing_id = %s",
                (reaction, telegram_user_id, listing_id),
            )


def count_unnotified_relevant_listings(conn: psycopg.Connection, telegram_user_id: int) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) AS n FROM user_listing_relevance "
            "WHERE telegram_user_id = %s AND is_relevant AND notified_at IS NULL",
            (telegram_user_id,),
        )
        return cursor.fetchone()["n"]


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


def get_relevance_score(conn: psycopg.Connection, telegram_user_id: int, listing_id: str) -> int:
    """This user's score for this listing, or 0 if it isn't (or is no longer)
    relevant to them — matches ``user_listing_relevance.score``'s own default.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT score FROM user_listing_relevance WHERE telegram_user_id = %s AND listing_id = %s",
            (telegram_user_id, listing_id),
        )
        row = cursor.fetchone()
        return row["score"] if row else 0


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


_PREFERENCE_COLUMNS = ("wants_pets", "budget_total_price", "min_area_m2")

_NO_PREFERENCES = {"wants_pets": None, "budget_total_price": None, "min_area_m2": None}


def get_user_preferences(conn: psycopg.Connection, telegram_user_id: int) -> dict:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT wants_pets, budget_total_price, min_area_m2 FROM user_preferences "
            "WHERE telegram_user_id = %s",
            (telegram_user_id,),
        )
        row = cursor.fetchone()
        return row if row else dict(_NO_PREFERENCES)


def set_user_preference(conn: psycopg.Connection, telegram_user_id: int, column: str, value) -> None:
    """Upsert one column of ``user_preferences``. ``column`` must be one of
    ``_PREFERENCE_COLUMNS`` — the onboarding flow is the only caller, so this is
    never fed anything beyond that fixed, internally-controlled set.
    """
    if column not in _PREFERENCE_COLUMNS:
        raise ValueError(f"Unknown preference column: {column}")
    ensure_bot_user(conn, telegram_user_id)
    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO user_preferences (telegram_user_id, {column}) VALUES (%s, %s) "
                f"ON CONFLICT (telegram_user_id) DO UPDATE SET {column} = EXCLUDED.{column}, updated_at = now()",
                (telegram_user_id, value),
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


def reset_user_onboarding(conn: psycopg.Connection, telegram_user_id: int) -> None:
    """Clear a user's saved search and preferences so the onboarding wizard
    (bot ``/onboarding``, Mini App "Restart onboarding") treats them as
    unonboarded again. Nulls ``search_url`` in place rather than deleting the
    ``bot_users`` row, so listing/relevance history (``ON DELETE CASCADE``
    from that row) survives, same as any other saved-search change.
    """
    ensure_bot_user(conn, telegram_user_id)
    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE bot_users SET search_url = NULL, updated_at = now() "
                "WHERE telegram_user_id = %s",
                (telegram_user_id,),
            )
            cursor.execute(
                "UPDATE user_preferences SET wants_pets = NULL, budget_total_price = NULL, "
                "min_area_m2 = NULL, updated_at = now() WHERE telegram_user_id = %s",
                (telegram_user_id,),
            )


def get_or_seed_user_search(conn: psycopg.Connection, telegram_user_id: int, default_url: str) -> str:
    """Return the user's saved search, creating one from ``default_url`` on first use."""
    ensure_bot_user(conn, telegram_user_id)
    existing = get_user_search(conn, telegram_user_id)
    if existing:
        return existing
    set_user_search(conn, telegram_user_id, default_url)
    return default_url


def list_user_languages(conn: psycopg.Connection) -> list[tuple[int, str]]:
    """Every known user's Telegram ID and chosen language — used to refresh
    each user's per-chat Telegram command menu on bot startup, since Telegram
    caches a per-chat override once set (``set_user_language``'s caller does
    this too) and won't otherwise surface a command added after that.
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT telegram_user_id, language_code FROM bot_users")
        return [(row["telegram_user_id"], row["language_code"]) for row in cursor.fetchall()]


def list_registered_users(conn: psycopg.Connection) -> list[int]:
    """Every Telegram user who has an active saved search (i.e. has used /parse
    or /parse_custom at least once) — what the scheduler and notify loop iterate.
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT telegram_user_id FROM bot_users WHERE search_url IS NOT NULL")
        return [row["telegram_user_id"] for row in cursor.fetchall()]


def admin_stats(conn: psycopg.Connection) -> dict:
    """Coarse counts for the Mini App's admin overview: how many Telegram
    accounts have ever messaged the bot, how many have picked a language,
    how many have an active saved search, and how many listings are cached.
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT count(*) AS n FROM users")
        tracked_users = cursor.fetchone()["n"]
        cursor.execute("SELECT count(*) AS n FROM bot_users")
        onboarded_users = cursor.fetchone()["n"]
        cursor.execute("SELECT count(*) AS n FROM bot_users WHERE search_url IS NOT NULL")
        registered_users = cursor.fetchone()["n"]
        cursor.execute("SELECT count(*) AS n FROM listings")
        total_listings = cursor.fetchone()["n"]
    return {
        "tracked_users": tracked_users,
        "onboarded_users": onboarded_users,
        "registered_users": registered_users,
        "total_listings": total_listings,
    }


_ADMIN_USERS_SQL = """
SELECT
    u.telegram_user_id,
    u.first_name,
    u.last_name,
    u.username,
    u.last_seen_at,
    bu.language_code,
    (bu.search_url IS NOT NULL) AS has_search,
    bu.created_at AS onboarded_at
FROM users u
LEFT JOIN bot_users bu ON bu.telegram_user_id = u.telegram_user_id
ORDER BY u.last_seen_at DESC
LIMIT 500
"""


def admin_list_users(conn: psycopg.Connection) -> list[dict]:
    """Every Telegram account the bot has ever seen, most-recently-active
    first, capped at 500 — a basic admin overview, not a paginated export.
    """
    with conn.cursor() as cursor:
        cursor.execute(_ADMIN_USERS_SQL)
        return cursor.fetchall()
