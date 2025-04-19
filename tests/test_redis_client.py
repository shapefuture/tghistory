import pytest
import fakeredis
from app.shared import redis_client
from app import config

def test_get_redis_connection(monkeypatch):
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr(redis_client, "_redis_instance", None)
    monkeypatch.setattr(redis_client, "redis", fakeredis)
    conf = config.settings
    result = redis_client.get_redis_connection(conf)
    assert result is not None

def test_get_rq_queue(monkeypatch):
    fake = fakeredis.FakeRedis()
    class FakeQueue:
        def __init__(self, name, connection):
            self.name = name
    monkeypatch.setattr(redis_client, "Queue", FakeQueue)
    conf = config.settings
    q = redis_client.get_rq_queue(fake, conf)
    assert q.name == conf.RQ_QUEUE_NAME