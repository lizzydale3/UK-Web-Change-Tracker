def test_health(app_client):
    r = app_client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, dict)
    assert data.get("status") == "ok"
    assert data.get("env") in {"testing", "development", "production"}
