"""Threadpool DB helper — mirrors the bot handlers' own ``asyncio.to_thread``
pattern so the sync, psycopg3-based ``src.db`` layer never blocks FastAPI's
event loop.
"""

from __future__ import annotations

import asyncio
from typing import Callable, TypeVar

from src import db

T = TypeVar("T")


async def run_db(fn: Callable[..., T], *args, **kwargs) -> T:
    def _call() -> T:
        with db.connect() as conn:
            db.ensure_schema(conn)
            return fn(conn, *args, **kwargs)

    return await asyncio.to_thread(_call)
