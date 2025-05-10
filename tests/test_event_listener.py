import pytest
import asyncio

from unittest.mock import AsyncMock, MagicMock, patch

from app.userbot import event_listener

@pytest.mark.asyncio
async def test_handle_job_completion_finished(monkeypatch):
    client = AsyncMock()
    fake_job = MagicMock()
    fake_job.is_finished = True
    fake_job.is_failed = False
    fake_job.result = {"summary": "sum"}
    monkeypatch.setattr("app.userbot.state.get_request_data", lambda rid: {"user_id": 1})
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda cfg: None)
    monkeypatch.setattr("app.userbot.results_sender.send_llm_result", AsyncMock())
    monkeypatch.setattr("rq.job.Job.fetch", lambda job_id, connection=None: fake_job)
    await event_listener.handle_job_completion(client, "jid", "rid", 2)
    event_listener.results_sender.send_llm_result.assert_awaited()

@pytest.mark.asyncio
async def test_handle_job_completion_failed(monkeypatch):
    client = AsyncMock()
    fake_job = MagicMock()
    fake_job.is_finished = False
    fake_job.is_failed = True
    fake_job.result = {"error": "fail"}
    monkeypatch.setattr("app.userbot.state.get_request_data", lambda rid: {"user_id": 1})
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda cfg: None)
    monkeypatch.setattr("app.userbot.results_sender.send_failure_message", AsyncMock())
    monkeypatch.setattr("rq.job.Job.fetch", lambda job_id, connection=None: fake_job)
    await event_listener.handle_job_completion(client, "jid", "rid", 2)
    event_listener.results_sender.send_failure_message.assert_awaited()

@pytest.mark.asyncio
async def test_handle_job_completion_missing_data(monkeypatch):
    client = AsyncMock()
    fake_job = MagicMock()
    fake_job.is_finished = True
    fake_job.is_failed = False
    fake_job.result = {"summary": "sum"}
    monkeypatch.setattr("app.userbot.state.get_request_data", lambda rid: None)
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda cfg: None)
    monkeypatch.setattr("rq.job.Job.fetch", lambda job_id, connection=None: fake_job)
    await event_listener.handle_job_completion(client, "jid", "rid", 2)

@pytest.mark.asyncio
async def test_listen_for_job_events_handles_decode_and_update(monkeypatch):
    # Simulate one pubsub message with status=SUCCESS
    class FakePubSub:
        def psubscribe(self, pattern): pass
        def punsubscribe(self): pass
        def listen(self):
            # Type "pmessage" is needed for the handler to process.
            yield {
                "type": "pmessage",
                "channel": b"request_status:rid",
                "data": b'{"job_id": "jid", "chat_id": 2, "status": "SUCCESS"}'
            }
    fake_redis = MagicMock()
    fake_redis.pubsub.return_value = FakePubSub()
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda cfg: fake_redis)
    monkeypatch.setattr("app.userbot.state.update_request_status", lambda rid, status: None)
    monkeypatch.setattr("app.userbot.ui.update_status_message_for_request", AsyncMock())
    monkeypatch.setattr("app.userbot.event_listener.handle_job_completion", AsyncMock())
    client = AsyncMock()
    # Should process one message and call update_status_message_for_request and handle_job_completion
    await asyncio.wait_for(event_listener.listen_for_job_events(client), timeout=1)
