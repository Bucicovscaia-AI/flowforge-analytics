"""FastAPI entry point.

Routes stay thin: validation, cleaning, KPIs, insights, reports and the
webhook live in app/services so they can be tested on their own.

When the React app has been built (frontend/dist), the same server also
serves it, so the whole application can run as one web service.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.config import APP_VERSION, Settings, load_settings
from app.routers import datasets, reports, system
from app.storage import Store

# Multipart framing adds a little to the file size; allow for it.
UPLOAD_OVERHEAD_BYTES = 64 * 1024


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(
        title="FlowForge Analytics API",
        version=APP_VERSION,
        description="Upload a sales CSV, clean it, calculate KPIs, generate insights and PDF reports.",
    )
    app.state.settings = settings
    app.state.store = Store(settings.data_dir)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def limit_body_size(request: Request, call_next):
        # Reject oversized uploads from the Content-Length header before the
        # body is read. The upload route checks the real size again.
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_upload_bytes + UPLOAD_OVERHEAD_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": {"message": f"The file is larger than {settings.max_upload_mb} MB.", "problems": []}},
            )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response

    app.include_router(system.router)
    app.include_router(datasets.router)
    app.include_router(reports.router)

    static_dir = settings.static_dir
    if (static_dir / "index.html").exists():
        root = static_dir.resolve()

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            # Unknown /api paths must stay 404s, not the React page.
            if path.startswith("api/") or path == "api":
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            candidate = (root / path).resolve()
            if path and candidate.is_file() and candidate.is_relative_to(root):
                return FileResponse(candidate)
            return FileResponse(root / "index.html")

    return app


app = create_app()
