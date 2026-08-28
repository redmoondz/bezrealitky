"""FastAPI entrypoint: the JSON API under ``/api``, the built React SPA under
everything else. Routers are included before the static mount so ``/api/*``
is never shadowed by the SPA's catch-all ``index.html`` fallback.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import charts, listings, meta, onboarding, search

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="Bezrealitky Mini App")
    app.include_router(meta.router, prefix="/api")
    app.include_router(onboarding.router, prefix="/api")
    app.include_router(listings.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(charts.router, prefix="/api")
    # Absent in local dev before `npm run build` has produced webapp/frontend/dist —
    # the API still works standalone (e.g. via curl) without it.
    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")
    return app


app = create_app()
