"""Long-running loop: re-scrape every registered user's own saved search.

Runs as the ``scheduler`` compose service (same image as the CLI, different
entrypoint) and ``run_once_for_user`` is also what the Telegram bot's ``/parse``
and ``/parse_custom`` call directly, so scheduled and manually triggered runs go
through one code path. Each Telegram user has their own independent saved search
(``bot_users.search_url``); a user with no saved search yet is simply skipped —
there is nothing registered to scrape for them until they run /parse once.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from copy import deepcopy

try:
    from . import db
    from .configuration import load_config
    from .scraper import Listing, discover_and_parse
except ImportError:  # Support: python3 src/scheduler.py
    import db  # type: ignore[no-redef]
    from configuration import load_config  # type: ignore[no-redef]
    from scraper import Listing, discover_and_parse  # type: ignore[no-redef]

LOGGER = logging.getLogger(__name__)

DEFAULT_INTERVAL_HOURS = 2.0


def user_config(base_config: dict, search_url: str) -> dict:
    """The shared scraper settings (timeout/delay/retries/user-agent) with one
    user's own search URL substituted in.
    """
    config = deepcopy(base_config)
    config["search"]["url"] = search_url
    return config


def run_once_for_user(
    telegram_user_id: int, search_url: str, base_config: dict
) -> tuple[list[Listing], list[str]]:
    """Scrape one user's saved search once and sync the results into Postgres."""
    listings, failures = discover_and_parse(user_config(base_config, search_url))
    with db.connect() as conn:
        db.ensure_schema(conn)
        db.sync_user_listings(conn, telegram_user_id, listings)
    if failures:
        LOGGER.error(
            "User %s: finished with %d failed publications", telegram_user_id, len(failures)
        )
    else:
        LOGGER.info("User %s: synced %d publications successfully", telegram_user_id, len(listings))
    return listings, failures


def run_once_for_all_users(base_config: dict) -> None:
    with db.connect() as conn:
        db.ensure_schema(conn)
        users = db.list_registered_users(conn)
    if not users:
        LOGGER.info("No registered users with a saved search yet; nothing to scrape")
        return
    for telegram_user_id in users:
        with db.connect() as conn:
            search_url = db.get_user_search(conn, telegram_user_id)
        if not search_url:
            continue
        try:
            run_once_for_user(telegram_user_id, search_url, base_config)
        except Exception:  # noqa: BLE001 - one user's failure must not skip the rest
            LOGGER.exception("Scrape cycle failed for user %s", telegram_user_id)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    interval_hours = float(os.environ.get("SCRAPE_INTERVAL_HOURS", DEFAULT_INTERVAL_HOURS))
    stop_event = threading.Event()

    def _handle_signal(signum: int, _frame: object) -> None:
        LOGGER.info("Received signal %d, stopping after the current cycle", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    while not stop_event.is_set():
        try:
            run_once_for_all_users(load_config())
        except Exception:  # noqa: BLE001 - a bad cycle must not kill the service
            LOGGER.exception("Scrape cycle failed; will retry next interval")
        stop_event.wait(interval_hours * 3600)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
