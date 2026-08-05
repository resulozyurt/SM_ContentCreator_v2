"""
FastAPI application entry point.

Phase 0 (current): the app boots and exposes a health check. Feature routers
(admin panel, pipeline actions) are wired in during later phases. See
docs/PROJECT_MEMORY.md for the roadmap.
"""

from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.config import get_settings

app = FastAPI(
    title="SM Content Creator v2",
    description="FieldPie & Evatro social media content generation system",
    version=__version__,
)


@app.get("/health", tags=["system"])
def health() -> dict:
    """Liveness probe used by Railway and local checks."""
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "env": settings.app_env,
    }


# TODO(phase-6): mount admin panel router (app.admin.routes)
# TODO(phase-3..4): mount pipeline action routers
