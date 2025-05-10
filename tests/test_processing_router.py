import os
import tempfile
from fastapi.testclient import TestClient
from app.main import app
from app.routers.processing import get_current_user

client = TestClient(app)

def test_status_page_not_found(monkeypatch):
    monkeypatch.setattr("app.crud.get_processing_request", lambda rid: None)
    resp = client.get("/status/req123", headers={"X-User-Id": "42"})
    assert resp.status_code == 404

def test_status_page_success(monkeypatch):
    class DummyReq:
        request_id = "req123"
        target_chat_id = 1
        status = "SUCCESS"
        custom_prompt = "prompt"
        tasks = [type("T", (), dict(summary="sum", participants_file=None, error=None))]
    monkeypatch.setattr("app.crud.get_processing_request", lambda rid: DummyReq())
    resp = client.get("/status/req123", headers={"X-User-Id": "42"})
    assert resp.status_code == 200
    assert "Chat Summarization Request Status" in resp.text

def test_api_status_unauthorized(monkeypatch):
    monkeypatch.setattr("app.crud.get_task_status", lambda rid: None)
    monkeypatch.setattr("app.crud.get_processing_request", lambda rid: None)
    resp = client.get("/api/status/req123", headers={"X-User-Id": "42"})
    assert resp.status_code == 404

def test_api_status_success(monkeypatch):
    class DummyStatus:
        def dict(self):
            return {"status": "SUCCESS"}
    monkeypatch.setattr("app.crud.get_task_status", lambda rid: DummyStatus())
    class DummyReq:
        user_id = 42
    monkeypatch.setattr("app.crud.get_processing_request", lambda rid: DummyReq())
    resp = client.get("/api/status/req123", headers={"X-User-Id": "42"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"

def test_download_file_notfound(monkeypatch):
    monkeypatch.setattr("app.crud.get_processing_request", lambda rid: None)
    resp = client.get("/download/req123/fake.txt", headers={"X-User-Id": "42"})
    assert resp.status_code == 404

def test_download_file_forbidden(monkeypatch):
    class DummyReq:
        user_id = 99
    monkeypatch.setattr("app.crud.get_processing_request", lambda rid: DummyReq())
    resp = client.get("/download/req123/fake.txt", headers={"X-User-Id": "42"})
    assert resp.status_code == 403

def test_download_file_success(monkeypatch, tmp_path):
    class DummyReq:
        user_id = 42
    fake_file = tmp_path / "file.txt"
    fake_file.write_text("hi")
    monkeypatch.setattr("app.crud.get_processing_request", lambda rid: DummyReq())
    monkeypatch.setattr("app.config.settings.OUTPUT_DIR_PATH", str(tmp_path))
    resp = client.get(f"/download/req123/{fake_file.name}", headers={"X-User-Id": "42"})
    assert resp.status_code == 200
    assert resp.content == b"hi"

def test_download_file_missing(monkeypatch, tmp_path):
    class DummyReq:
        user_id = 42
    monkeypatch.setattr("app.crud.get_processing_request", lambda rid: DummyReq())
    monkeypatch.setattr("app.config.settings.OUTPUT_DIR_PATH", str(tmp_path))
    resp = client.get("/download/req123/doesnotexist.txt", headers={"X-User-Id": "42"})
    assert resp.status_code == 404

def test_status_page_auth_required():
    resp = client.get("/status/req123")
    assert resp.status_code == 401

def test_api_status_auth_required():
    resp = client.get("/api/status/req123")
    assert resp.status_code == 401

def test_download_file_auth_required():
    resp = client.get("/download/req123/file.txt")
    assert resp.status_code == 401
