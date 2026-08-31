"""One-off backfill: reclassify ``pets_friendly`` for listings already in
Postgres that still show ``NULL`` (unknown).

A ``NULL`` there isn't necessarily a permanent fact — the live scraper's own
fallback (:func:`src.scraper.extract_pets_friendly`) only classifies the
description at scrape time, so a row synced before that fallback existed, or
before a taxonomy fix started catching phrasing it used to miss (see
``pets_taxonomy_design`` notes), can sit at ``NULL`` even though its stored
description clearly states a policy. Re-running :func:`classify_pets_friendly`
against the stored description can resolve some of those; anything it still
can't resolve is left ``NULL`` — same "never guess" contract as the live
scraper.
"""

from __future__ import annotations

import logging

try:
    from . import db
    from .pets import classify_pets_friendly
except ImportError:  # Support: python3 src/backfill_pets.py
    import db  # type: ignore[no-redef]
    from pets import classify_pets_friendly  # type: ignore[no-redef]

LOGGER = logging.getLogger(__name__)


def backfill() -> tuple[int, int]:
    """Returns ``(updated, checked)``."""
    with db.connect() as conn:
        db.ensure_schema(conn)
        rows = db.fetch_listings_missing_pets_friendly(conn)
        updated = 0
        for row in rows:
            classification = classify_pets_friendly(row["description"])
            if classification == "":
                continue
            db.update_pets_friendly(conn, row["listing_id"], classification == "True")
            updated += 1
    LOGGER.info("Reclassified pets_friendly for %d of %d previously-unknown listings", updated, len(rows))
    return updated, len(rows)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    updated, checked = backfill()
    print(f"Reclassified {updated} of {checked} previously-unknown listing(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
