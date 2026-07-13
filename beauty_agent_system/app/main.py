"""FastAPI application entrypoint: mounts the API routers + the Jinja2 admin
dashboard and starts the APScheduler background jobs on startup."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import (
    approvals,
    daily_summary,
    insights,
    knowledge_base,
    leads,
    system_health,
    tasks,
    updates,
    webhook,
)
from app.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    _scheduler = start_scheduler()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


app = FastAPI(title="Beauty SaaS Growth & Support System", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(webhook.router)
app.include_router(daily_summary.router)
app.include_router(updates.router)
app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(leads.router)
app.include_router(system_health.router)
app.include_router(insights.router)
app.include_router(knowledge_base.router)


@app.get("/")
def root():
    return RedirectResponse(url="/admin/daily-summary")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
