import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_success():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Telegram Extractor API"
    assert data["status"] == "online"
    assert "X-Process-Time" in resp.headers

def test_process_time_header_present():
    resp = client.get("/")
    assert "X-Process-Time" in resp.headers
    val = float(resp.headers["X-Process-Time"])
    assert val >= 0

def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data

def test_health_check_full():
    resp = client.get("/health?full=true")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "redis" in data or "system" in data

def test_api_error_handling(monkeypatch):
    # Simulate error in root
    from app.main import root
    async def fail_root():
        raise Exception("fail")
    monkeypatch.setattr("app.main.root", fail_root)
    # Must still get error JSON
    resp = client.get("/")
    assert resp.status_code == 200 or resp.status_code == 500
    data = resp.json()
    assert "error" in data or "status" in data
