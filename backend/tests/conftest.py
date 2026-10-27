"""Shared fixtures: every test gets its own app with a temporary data folder,
and AI and webhook settings switched off unless a test turns them on."""

from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app

VALID_CSV = (
    "order_id,order_date,product,product_category,region,channel,customer_type,quantity,unit_price\n"
    "A1,2026-01-05,Lamp,Home,North,Online,New,2,10.00\n"
    "A1,2026-01-05,Mug,Home,North,Online,New,1,5.00\n"
    "A2,2026-01-20,Jacket,Clothing,South,In-store,Returning,1,50.00\n"
    "A3,2026-02-03,Lamp,Home,north,Online,,3,10.00\n"
    "A4,2026-02-14,Jacket,Clothing,South,Phone,Business,2,50.00\n"
)


@pytest.fixture
def settings(tmp_path):
    base = load_settings()
    return replace(
        base,
        data_dir=tmp_path / "data",
        static_dir=tmp_path / "no-static",
        ai_api_key="",
        make_webhook_url="",
        make_webhook_api_key="",
        max_upload_mb=1,
    )


@pytest.fixture
def client(settings):
    return TestClient(create_app(settings))


def upload(client: TestClient, content: str | bytes, name: str = "orders.csv", content_type: str = "text/csv", synthetic: bool = True):
    data = content.encode() if isinstance(content, str) else content
    return client.post(
        "/api/datasets/upload",
        files={"file": (name, data, content_type)},
        data={"synthetic": "true" if synthetic else "false"},
    )
