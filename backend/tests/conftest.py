from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.container import build_services

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = REPO_ROOT / "sample-data" / "flowforge-retail-sample.csv"

KNOWN_CSV = """order_id,order_date,category,region,quantity,unit_price,revenue
1,2025-01-05,A,North,2,10,20
2,2025-01-20,B,South,1,30,30
3,2025-02-03,A,North,3,10,30
4,2025-02-15,A,South,1,50,50
5,2025-03-01,B,North,4,10,40
6,2025-03-31,B,South,2,30,60
"""


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", sample_data_path=SAMPLE_PATH, max_upload_mb=1)


@pytest.fixture
def make_client(settings):
    def factory(*, insight_provider=None, webhook_client=None, **overrides) -> TestClient:
        configured = replace(settings, **overrides)
        services = build_services(configured, insight_provider=insight_provider, webhook_client=webhook_client)
        return TestClient(create_app(configured, services))

    return factory


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


def upload(client: TestClient, content: str | bytes, filename: str = "data.csv", content_type: str = "text/csv", name=None):
    data = content.encode("utf-8") if isinstance(content, str) else content
    form = {"name": name} if name else None
    return client.post("/api/datasets/upload", files={"file": (filename, data, content_type)}, data=form)


@pytest.fixture
def known_dataset(client) -> str:
    response = upload(client, KNOWN_CSV, "known.csv")
    assert response.status_code == 201, response.text
    return response.json()["id"]
