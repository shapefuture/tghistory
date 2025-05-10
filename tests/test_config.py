import os
import pytest
from pydantic import ValidationError
from app.config import Settings

def test_settings_valid(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "a"*32)
    monkeypatch.setenv("TELEGRAM_SESSION_PATH", "/tmp/session.session")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    s = Settings()
    assert s.TELEGRAM_API_ID == 123
    assert s.TELEGRAM_API_HASH == "a"*32
    assert s.REDIS_URL.startswith("redis://")

def test_settings_invalid_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "-1")
    monkeypatch.setenv("TELEGRAM_API_HASH", "a"*32)
    monkeypatch.setenv("TELEGRAM_SESSION_PATH", "/tmp/session.session")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    with pytest.raises(ValueError):
        Settings()

def test_settings_invalid_hash(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "bad")
    monkeypatch.setenv("TELEGRAM_SESSION_PATH", "/tmp/session.session")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    with pytest.raises(ValueError):
        Settings()

def test_settings_invalid_redis(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "a"*32)
    monkeypatch.setenv("TELEGRAM_SESSION_PATH", "/tmp/session.session")
    monkeypatch.setenv("REDIS_URL", "notredis://foo")
    with pytest.raises(ValueError):
        Settings()
