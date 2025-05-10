import pytest
import time
from unittest.mock import MagicMock
from app.shared.rate_limiter import RateLimiter

def test_check_rate_limit_allowed(monkeypatch):
    fake_redis = MagicMock()
    fake_redis.zcard.return_value = 0
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    ok, result = RateLimiter.check_rate_limit(1, "foo", 5, 60)
    assert ok is True
    assert result["allowed"] is True

def test_check_rate_limit_blocked(monkeypatch):
    fake_redis = MagicMock()
    fake_redis.zcard.return_value = 5
    fake_redis.zrange.return_value = [(b"t", time.time()-30)]
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    ok, result = RateLimiter.check_rate_limit(1, "foo", 5, 60)
    assert ok is False
    assert result["allowed"] is False

def test_check_rate_limit_error(monkeypatch):
    def raise_exc(*a, **kw): raise Exception("fail")
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", raise_exc)
    ok, result = RateLimiter.check_rate_limit(1, "foo", 5, 60)
    assert ok is True
    assert "error" in result

def test_get_rate_limits(monkeypatch):
    fake_redis = MagicMock()
    fake_redis.scan_iter.return_value = [b"rate:user:1:foo", b"rate:user:1:bar"]
    fake_redis.zrange.return_value = [(b"k", time.time()-10), (b"k", time.time())]
    fake_redis.ttl.return_value = 120
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    res = RateLimiter.get_rate_limits(1)
    assert isinstance(res, dict)
    assert "foo" in res or "bar" in res
