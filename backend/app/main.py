"""FastAPI entry point. Routes stay thin; data processing will live in
separate modules (added in Stages 3 and 4) so it can be tested on its own."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_VERSION, FRONTEND_ORIGIN

app = FastAPI(title="FlowForge Analytics API", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    """Lets the frontend (and later Make.com) check the API is running."""
    return {"status": "ok", "version": APP_VERSION}
