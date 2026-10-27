"""Shared request helpers for the routers."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.config import Settings
from app.storage import Store


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_store(request: Request) -> Store:
    return request.app.state.store


def require_analysis(store: Store, analysis_id: str) -> dict:
    analysis = store.get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found. Upload or select a dataset again.")
    return analysis
