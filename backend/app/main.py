"""FlowForge Analytics API application.

Run with:  uvicorn app.main:create_app --factory --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import analysis, automation, datasets, reports, system
from app.config import APP_NAME, APP_VERSION, Settings, get_settings
from app.errors import NotFoundError, register_error_handlers
from app.services.container import Services, build_services

API_PREFIX = "/api"


def _mount_frontend(app: FastAPI, settings: Settings) -> None:
    """Serve a production build of the frontend from the API process, if configured."""
    dist = settings.frontend_dist_dir
    if not dist or not (dist / "index.html").is_file():
        return
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")
    index = dist / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            # Unknown API routes get a JSON 404, not the application page.
            raise NotFoundError("API endpoint not found.", code="endpoint_not_found")
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = FastAPI(
        title=f"{APP_NAME} API",
        version=APP_VERSION,
        description="Import CSV data, assess and improve its quality, analyse it, generate insights and reports, and trigger automation workflows.",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
        openapi_url=f"{API_PREFIX}/openapi.json",
    )
    app.state.services = services or build_services(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
    register_error_handlers(app)

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response

    for router in (system.router, datasets.router, analysis.router, reports.router, automation.router):
        app.include_router(router, prefix=API_PREFIX)
    _mount_frontend(app, settings)
    return app
