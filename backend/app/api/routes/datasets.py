from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status

from app.api.deps import DatasetId, get_services
from app.engine.cleaning import OPERATIONS
from app.errors import PayloadTooLarge, UnsupportedMediaType, ValidationFailed
from app.schemas.datasets import (
    CleaningRequest,
    CleaningResult,
    ColumnMappingUpdate,
    DatasetDetail,
    DatasetPreview,
    DatasetRename,
    DatasetSummary,
    OperationDescription,
    QualityReportOut,
)
from app.services.container import Services

router = APIRouter(tags=["Datasets"])

ACCEPTED_EXTENSIONS = (".csv", ".txt")
ACCEPTED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "text/plain",
    "application/vnd.ms-excel",
    "application/octet-stream",
    "text/comma-separated-values",
    "",
}
CHUNK_SIZE = 1024 * 1024


async def _read_limited(upload: UploadFile, limit: int) -> bytes:
    """Read an upload in chunks, stopping as soon as it exceeds the size limit."""
    chunks, total = [], 0
    while chunk := await upload.read(CHUNK_SIZE):
        total += len(chunk)
        if total > limit:
            raise PayloadTooLarge(f"The file is larger than the {limit // (1024 * 1024)} MB limit.")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/datasets/upload", response_model=DatasetSummary, status_code=status.HTTP_201_CREATED, summary="Upload a CSV file")
async def upload_dataset(
    request: Request,
    file: UploadFile = File(..., description="CSV file"),
    name: str | None = Form(None, max_length=120),
    services: Services = Depends(get_services),
) -> dict:
    limit = services.settings.max_upload_bytes
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit + 64 * 1024:
        raise PayloadTooLarge(f"The file is larger than the {services.settings.max_upload_mb} MB limit.")
    filename = file.filename or ""
    if not filename.lower().endswith(ACCEPTED_EXTENSIONS):
        raise UnsupportedMediaType("Only CSV files (.csv) are supported.")
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ACCEPTED_CONTENT_TYPES:
        raise UnsupportedMediaType(f"Files of type '{content_type}' are not accepted. Upload a CSV file.")
    data = await _read_limited(file, limit)
    await file.close()
    return services.datasets.import_csv(data, filename=filename, name=name)


@router.post(
    "/datasets/sample",
    response_model=DatasetSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Import the synthetic sample dataset",
)
def load_sample(services: Services = Depends(get_services)) -> dict:
    return services.datasets.import_sample()


@router.get("/datasets", response_model=list[DatasetSummary], summary="List datasets")
def list_datasets(services: Services = Depends(get_services)) -> list[dict]:
    return services.datasets.list_records()


@router.get("/datasets/{dataset_id}", response_model=DatasetDetail, summary="Dataset metadata and column profile")
def get_dataset(dataset_id: str = DatasetId, services: Services = Depends(get_services)) -> dict:
    return services.datasets.detail(dataset_id)


@router.patch("/datasets/{dataset_id}", response_model=DatasetSummary, summary="Rename a dataset")
def rename_dataset(body: DatasetRename, dataset_id: str = DatasetId, services: Services = Depends(get_services)) -> dict:
    return services.datasets.rename(dataset_id, body.name)


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a dataset and its files")
def delete_dataset(dataset_id: str = DatasetId, services: Services = Depends(get_services)) -> Response:
    services.datasets.delete(dataset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/datasets/{dataset_id}/column-mapping", response_model=DatasetDetail, summary="Set business column roles")
def update_mapping(body: ColumnMappingUpdate, dataset_id: str = DatasetId, services: Services = Depends(get_services)) -> dict:
    return services.datasets.update_mapping(dataset_id, body.mapping)


@router.get("/datasets/{dataset_id}/preview", response_model=DatasetPreview, summary="Preview rows")
def preview(
    dataset_id: str = DatasetId,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    services: Services = Depends(get_services),
) -> dict:
    return services.datasets.preview(dataset_id, offset, limit)


@router.get("/datasets/{dataset_id}/export.csv", summary="Download the working copy as CSV")
def export_dataset(dataset_id: str = DatasetId, services: Services = Depends(get_services)) -> Response:
    record = services.datasets.get_record(dataset_id)
    content = services.datasets.export_working_csv(dataset_id)
    filename = "".join(ch if ch.isalnum() else "-" for ch in record["name"]).strip("-").lower()[:60] or "dataset"
    return Response(
        content, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'}
    )


@router.get("/datasets/{dataset_id}/quality", response_model=QualityReportOut, summary="Run data quality checks")
def quality(dataset_id: str = DatasetId, services: Services = Depends(get_services)) -> dict:
    return services.datasets.quality(dataset_id).to_dict()


@router.get("/cleaning/operations", response_model=list[OperationDescription], summary="Supported cleaning operations")
def cleaning_operations() -> list[dict]:
    return [operation.describe() for operation in OPERATIONS.values()]


def _check_operation(body: CleaningRequest) -> None:
    if body.operation not in OPERATIONS:
        raise ValidationFailed(f"Unknown cleaning operation '{body.operation}'.", code="invalid_operation")


@router.post(
    "/datasets/{dataset_id}/cleaning/preview",
    response_model=CleaningResult,
    summary="Preview a cleaning operation without saving it",
)
def preview_cleaning(body: CleaningRequest, dataset_id: str = DatasetId, services: Services = Depends(get_services)) -> dict:
    _check_operation(body)
    return services.datasets.preview_operation(dataset_id, body.operation, body.params)


@router.post("/datasets/{dataset_id}/cleaning/apply", response_model=CleaningResult, summary="Apply a cleaning operation")
def apply_cleaning(body: CleaningRequest, dataset_id: str = DatasetId, services: Services = Depends(get_services)) -> dict:
    _check_operation(body)
    return services.datasets.apply_operation(dataset_id, body.operation, body.params)


@router.post(
    "/datasets/{dataset_id}/cleaning/reset", response_model=DatasetDetail, summary="Restore the originally imported data"
)
def reset_cleaning(dataset_id: str = DatasetId, services: Services = Depends(get_services)) -> dict:
    return services.datasets.reset(dataset_id)
