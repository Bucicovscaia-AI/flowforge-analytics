"""Dataset upload, sample datasets, analyses and insights."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import Settings
from app.deps import get_settings, get_store, require_analysis
from app.samples import list_samples, sample_path
from app.services.ai_insights import build_ai_summary, generate_insights
from app.services.csv_loader import DatasetError, load_csv
from app.services.pipeline import run_analysis
from app.storage import Store

router = APIRouter(prefix="/api", tags=["datasets"])


def _analyse(raw: bytes, name: str, content_type: str | None, settings: Settings, *, synthetic: bool, sample_id: str | None = None) -> dict:
    try:
        loaded = load_csv(
            raw,
            name,
            content_type,
            max_bytes=settings.max_upload_bytes,
            max_rows=settings.max_rows,
            max_columns=settings.max_columns,
        )
    except DatasetError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "problems": exc.problems}) from None
    return run_analysis(loaded, synthetic=synthetic, sample_id=sample_id)


@router.get("/samples")
def samples(settings: Settings = Depends(get_settings)) -> list[dict]:
    return list_samples(settings.sample_data_dir)


@router.post("/samples/{sample_id}/analyse", status_code=201)
async def analyse_sample(sample_id: str, settings: Settings = Depends(get_settings), store: Store = Depends(get_store)) -> dict:
    path = sample_path(settings.sample_data_dir, sample_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Sample dataset not found.")
    analysis = await run_in_threadpool(_analyse, path.read_bytes(), path.name, "text/csv", settings, synthetic=True, sample_id=sample_id)
    store.save_analysis(analysis)
    return analysis


@router.post("/datasets/upload", status_code=201)
async def upload_dataset(
    file: UploadFile = File(..., description="CSV file of sales order lines"),
    synthetic: bool = Form(True, description="True when the file holds synthetic or demo data"),
    settings: Settings = Depends(get_settings),
    store: Store = Depends(get_store),
) -> dict:
    # Read one byte more than the limit so an oversized file is detected
    # without holding an arbitrarily large body in memory.
    raw = await file.read(settings.max_upload_bytes + 1)
    analysis = await run_in_threadpool(_analyse, raw, file.filename or "upload.csv", file.content_type, settings, synthetic=synthetic)
    store.save_analysis(analysis)
    return analysis


@router.get("/analyses")
def analyses(store: Store = Depends(get_store)) -> list[dict]:
    return store.list_analyses()


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str, store: Store = Depends(get_store)) -> dict:
    return require_analysis(store, analysis_id)


@router.get("/analyses/{analysis_id}/ai-payload")
def ai_payload(analysis_id: str, store: Store = Depends(get_store)) -> dict:
    """Shows exactly what would be sent to the AI service (no raw rows)."""
    return build_ai_summary(require_analysis(store, analysis_id))


@router.post("/analyses/{analysis_id}/insights")
async def insights(analysis_id: str, settings: Settings = Depends(get_settings), store: Store = Depends(get_store)) -> dict:
    analysis = require_analysis(store, analysis_id)
    result = await run_in_threadpool(generate_insights, analysis, settings)
    analysis["insights"] = result
    store.save_analysis(analysis)
    return result
