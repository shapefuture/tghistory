import pytest
from fastapi.testclient import TestClient
from app.main import app
import os

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "sample_admin_token")

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data

def test_health_components_auth_required():
    resp = client.get("/health/components")
    assert resp.status_code == 401

def test_health_components_success(monkeypatch):
    token = ADMIN_TOKEN
    resp = client.get("/health/components", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert "redis" in data or "system" in data

def test_metrics_system_auth_required():
    resp = client.get("/metrics/system")
    assert resp.status_code == 401

def test_metrics_system_success(monkeypatch):
    token = ADMIN_TOKEN
    monkeypatch.setattr("app.shared.metrics.MetricsRetriever.get_system_metrics", lambda days, interval: {"foo": "bar"})
    resp = client.get("/metrics/system", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    assert resp.json()["metrics"] == {"foo": "bar"}

def test_metrics_api_success(monkeypatch):
    token = ADMIN_TOKEN
    monkeypatch.setattr("app.shared.metrics.MetricsRetriever.get_api_metrics", lambda days, endpoints: {"api": "v"})
    resp = client.get("/metrics/api", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    assert resp.json()["metrics"] == {"api": "v"}

def test_metrics_users_success(monkeypatch):
    token = ADMIN_TOKEN
    monkeypatch.setattr("app.shared.metrics.MetricsRetriever.get_user_metrics", lambda user_id, days: {"m": 1})
    resp = client.get("/metrics/users/123", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    assert resp.json()["m"] == 1

def test_metrics_users_notfound(monkeypatch):
    token = ADMIN_TOKEN
    monkeypatch.setattr("app.shared.metrics.MetricsRetriever.get_user_metrics", lambda user_id, days: {})
    resp = client.get("/metrics/users/999", headers={"X-Admin-Token": token})
    assert resp.status_code == 404

def test_metrics_jobs_success(monkeypatch):
    token = ADMIN_TOKEN
    monkeypatch.setattr("app.shared.metrics.MetricsRetriever.get_job_metrics", lambda job_id: {"k": 1})
    resp = client.get("/metrics/jobs/jobid", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    assert resp.json()["k"] == 1

def test_metrics_jobs_notfound(monkeypatch):
    token = ADMIN_TOKEN
    monkeypatch.setattr("app.shared.metrics.MetricsRetriever.get_job_metrics", lambda job_id: {})
    resp = client.get("/metrics/jobs/none", headers={"X-Admin-Token": token})
    assert resp.status_code == 404

def test_metrics_api_auth_required():
    resp = client.get("/metrics/api")
    assert resp.status_code == 401
