"""One-time migration: import the legacy scraper CSV into Postgres.

Older CSV exports predate the ``floor_number``/``floor_total``/``pets_friendly``/
``furnished`` columns, so those are backfilled here from the raw
``floor``/``description``/``fully_furnished`` text using the same parsers the
live scraper uses. Imported rows land as
``is_relevant = TRUE``; the next scheduled sync (:mod:`src.scheduler`) recomputes
relevance against whatever search config is actually active.
"""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path

try:
    from . import db
    from .floor import parse_floor
    from .furnished import parse_furnished
    from .pets import classify_pets_friendly
    from .scraper import CSV_FIELDS, Listing
except ImportError:  # Support: python3 src/migrate.py
    import db  # type: ignore[no-redef]
    from floor import parse_floor  # type: ignore[no-redef]
    from furnished import parse_furnished  # type: ignore[no-redef]
    from pets import classify_pets_friendly  # type: ignore[no-redef]
    from scraper import CSV_FIELDS, Listing  # type: ignore[no-redef]

LOGGER = logging.getLogger(__name__)

DEFAULT_CSV_PATH = Path("output/bezrealitky_listings.csv")


def _row_to_listing(row: dict) -> Listing:
    data = {field: (row.get(field) or "") for field in CSV_FIELDS}
    if not data["floor_number"] and not data["floor_total"]:
        data["floor_number"], data["floor_total"] = parse_floor(data["floor"])
    if not data["pets_friendly"]:
        data["pets_friendly"] = classify_pets_friendly(data["description"])
    if not data["furnished"]:
        data["furnished"] = parse_furnished(data["fully_furnished"])
    return Listing(**data)


def migrate(csv_path: Path) -> int:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {csv_path}")
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        listings = [_row_to_listing(row) for row in csv.DictReader(handle)]

    with db.connect() as conn:
        db.ensure_schema(conn)
        imported = db.import_listings(conn, listings)
    LOGGER.info("Imported %d listings from %s into Postgres", imported, csv_path)
    return imported


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Import the legacy scraper CSV into Postgres."
    )
    parser.add_argument(
        "--csv", type=Path, default=DEFAULT_CSV_PATH, help="path to the CSV file to import"
    )
    args = parser.parse_args()
    migrate(args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
