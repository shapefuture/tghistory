import pytest
import time
from unittest.mock import MagicMock, patch
from app.shared.metrics import MetricsCollector, MetricsRetriever

def test_record_job_metrics(monkeypatch):
    fake_redis = MagicMock()
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    ok = MetricsCollector.record_job_metrics("jobid", {"foo": "bar"})
    assert ok is True
    fake_redis.hset.assert_called()

def test_record_user_metrics(monkeypatch):
    fake_redis = MagicMock()
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    ok = MetricsCollector.record_user_metrics(1, "test", {"baz": "qux"})
    assert ok is True
    fake_redis.lpush.assert_called()

def test_record_system_metrics(monkeypatch):
    fake_redis = MagicMock()
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    monkeypatch.setattr("psutil.cpu_percent", lambda interval: 33.3)
    monkeypatch.setattr("psutil.virtual_memory", lambda: MagicMock(percent=33.3, used=1024*1024*2))
    monkeypatch.setattr("psutil.disk_usage", lambda path: MagicMock(percent=22.2, used=1024*1024*3))
    monkeypatch.setattr("psutil.process_iter", lambda args: [])
    monkeypatch.setattr("os.getloadavg", lambda: (1.1, 0, 0))
    ok = MetricsCollector.record_system_metrics()
    assert ok is True

def test_record_api_metrics(monkeypatch):
    fake_redis = MagicMock()
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    fake_redis.hget.side_effect = [b"1", b"0"]
    ok = MetricsCollector.record_api_metrics("/api/test", 1.5, 200)
    assert ok is True

def test_get_job_metrics_empty(monkeypatch):
    fake_redis = MagicMock()
    fake_redis.hgetall.return_value = {}
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    res = MetricsRetriever.get_job_metrics("none")
    assert res == {}

def test_get_user_metrics_empty(monkeypatch):
    fake_redis = MagicMock()
    fake_redis.hgetall.return_value = {}
    fake_redis.lrange.return_value = []
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    res = MetricsRetriever.get_user_metrics(1, 1)
    assert isinstance(res, dict)

def test_get_system_metrics_empty(monkeypatch):
    fake_redis = MagicMock()
    fake_redis.lrange.return_value = []
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    res = MetricsRetriever.get_system_metrics(1, 5)
    assert isinstance(res, dict)

def test_get_api_metrics_empty(monkeypatch):
    fake_redis = MagicMock()
    fake_redis.scan_iter.return_value = []
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    res = MetricsRetriever.get_api_metrics(1, None)
    assert isinstance(res, dict)
