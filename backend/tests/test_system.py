from app.config import Settings


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "name": "FlowForge Analytics", "version": "1.0.0"}


def test_system_status_without_integrations(client):
    body = client.get("/api/system/status").json()
    assert body["ai"]["configured"] is False
    assert body["automation_configured"] is False
    assert body["limits"]["max_upload_mb"] == 1


def test_system_status_never_exposes_secrets(make_client):
    client = make_client(
        ai_provider="unsupported-provider",
        ai_api_key="sk-test-secret-value",
        make_webhook_url="https://hook.eu1.make.com/private-token-abc",
        make_webhook_secret="signing-secret",
    )
    for path in ("/api/system/status", "/api/automation/status", "/api/health", "/api/openapi.json"):
        text = client.get(path).text
        assert "sk-test-secret-value" not in text
        assert "private-token-abc" not in text
        assert "signing-secret" not in text


def test_unknown_route_returns_json_error(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_security_headers(client):
    response = client.get("/api/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_settings_repr_hides_secrets(tmp_path):
    settings = Settings(data_dir=tmp_path, sample_data_path=tmp_path / "x.csv", ai_api_key="hidden", make_webhook_url="https://x")
    assert "hidden" not in repr(settings)
    assert "https://x" not in repr(settings)


def test_serves_built_frontend_with_client_side_routes(make_client, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>FlowForge</title>")
    (dist / "assets" / "app.js").write_text("console.log('ok')")
    (dist / "favicon.svg").write_text("<svg></svg>")
    client = make_client(frontend_dist_dir=dist)

    assert "FlowForge" in client.get("/").text
    assert "FlowForge" in client.get("/reports/history").text
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/favicon.svg").text == "<svg></svg>"
    assert client.get("/api/health").json()["status"] == "ok"

    missing = client.get("/api/does-not-exist")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "endpoint_not_found"
    # Path traversal outside the build folder falls back to the application page.
    assert "FlowForge" in client.get("/..%2F..%2Fetc%2Fpasswd").text
