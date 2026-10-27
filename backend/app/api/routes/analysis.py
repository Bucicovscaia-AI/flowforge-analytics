from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import DatasetId, get_services
from app.schemas.analysis import (
    AggregateResult,
    AnalysisResult,
    DistributionResult,
    InsightRequest,
    InsightResult,
    TimeSeriesResult,
)
from app.services.container import Services

router = APIRouter(tags=["Analysis"])

Aggregation = Literal["sum", "mean", "median", "count", "min", "max"]


@router.get("/datasets/{dataset_id}/analysis", response_model=AnalysisResult, summary="Full analysis of a dataset")
def analysis(dataset_id: str = DatasetId, services: Services = Depends(get_services)) -> dict:
    return services.datasets.analysis(dataset_id)


@router.get("/datasets/{dataset_id}/charts/aggregate", response_model=AggregateResult, summary="Grouped values for a bar chart")
def aggregate(
    dataset_id: str = DatasetId,
    group_by: str = Query(..., min_length=1, max_length=200),
    value: str | None = Query(None, max_length=200, description="Numeric column; omit to count rows"),
    agg: Aggregation = "sum",
    top_n: int = Query(15, ge=1, le=100),
    services: Services = Depends(get_services),
) -> dict:
    return services.datasets.aggregate_chart(dataset_id, group_by, value, agg, top_n)


@router.get("/datasets/{dataset_id}/charts/timeseries", response_model=TimeSeriesResult, summary="Values per time period")
def timeseries(
    dataset_id: str = DatasetId,
    date_column: str | None = Query(None, max_length=200),
    value: str | None = Query(None, max_length=200),
    agg: Aggregation = "sum",
    granularity: Literal["auto", "day", "week", "month", "quarter", "year"] = "auto",
    services: Services = Depends(get_services),
) -> dict:
    return services.datasets.time_series_chart(dataset_id, date_column, value, agg, granularity)


@router.get(
    "/datasets/{dataset_id}/charts/distribution", response_model=DistributionResult, summary="Histogram of a numeric column"
)
def distribution(
    dataset_id: str = DatasetId,
    column: str = Query(..., min_length=1, max_length=200),
    bins: int = Query(20, ge=2, le=60),
    services: Services = Depends(get_services),
) -> dict:
    return services.datasets.distribution_chart(dataset_id, column, bins)


@router.get("/datasets/{dataset_id}/charts/aggregate.csv", summary="Download grouped values as CSV")
def aggregate_csv(
    dataset_id: str = DatasetId,
    group_by: str = Query(..., min_length=1, max_length=200),
    value: str | None = Query(None, max_length=200),
    agg: Aggregation = "sum",
    services: Services = Depends(get_services),
) -> Response:
    content = services.datasets.export_aggregate_csv(dataset_id, group_by, value, agg)
    return Response(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="grouped-results.csv"'},
    )


@router.post("/datasets/{dataset_id}/insights", response_model=InsightResult, summary="Generate insights")
def insights(body: InsightRequest, dataset_id: str = DatasetId, services: Services = Depends(get_services)) -> dict:
    return services.insights.generate(dataset_id, use_ai=body.use_ai)
