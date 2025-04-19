import pytest
from app.worker import tasks

def test_publish_status_handles_exceptions(monkeypatch):
    class DummyRedis:
        def publish(self, chan, msg):
            raise Exception("fail")
    monkeypatch.setattr(tasks, "get_redis_connection", lambda settings: DummyRedis())
    # Should not raise
    def fake_job(): pass
    tasks.job = fake_job
    tasks.extract_and_summarize_data("chat", "/tmp/sess", "user", "req", "prompt") # Will fail, but should not blow up on publish_status exception