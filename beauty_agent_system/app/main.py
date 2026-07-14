"""FastAPI application entrypoint: mounts the Virtual Office (a single page)
and starts the APScheduler (currently no jobs -- see app/scheduler.py)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import office
from app.routers import chatwoot as chatwoot_router
from app.routers import facebook as facebook_router
from app.routers import tiktok as tiktok_router
from app.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    # When no NEON_DATABASE_URL is set the engine falls back to a local SQLite
    # file.  Create all tables so the app doesn't 500 on the very first request.
    from app.config import get_settings
    from app.database import Base, get_engine
    if not get_settings().neon_database_url:
        import logging
        logging.getLogger("beauty_agent_system").warning(
            "NEON_DATABASE_URL not set — using local SQLite fallback and "
            "auto-creating tables.  Set the secret to switch to Neon."
        )
        Base.metadata.create_all(bind=get_engine())
    _scheduler = start_scheduler()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


app = FastAPI(title="CSC Virtual Office", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(office.router)
app.include_router(chatwoot_router.router)
app.include_router(facebook_router.router)
app.include_router(tiktok_router.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
