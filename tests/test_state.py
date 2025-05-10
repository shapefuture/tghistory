import fakeredis
import pytest

from app.userbot import state

@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = fakeredis.FakeStrictRedis()
    monkeypatch.setattr(state, "get_redis_connection", lambda _: fake)
    yield fake

def test_pending_prompt_state_lifecycle():
    user_id = 123
    request_id = "req1"
    assert state.set_pending_prompt_state(user_id, request_id) is True
    assert state.get_pending_state(user_id) == request_id
    assert state.clear_pending_state(user_id) is True
    assert state.get_pending_state(user_id) is None

def test_store_request_data():
    rid = "req2"
    d = {"foo": "bar", "num": "42"}
    assert state.store_request_data(rid, d) is True
    val = state.get_request_data(rid)
    assert isinstance(val, dict)
    assert val.get("foo") == "bar"
    assert val.get("num") == "42"

def test_update_request_status():
    rid = "req3"
    state.store_request_data(rid, {"status": "foo"})
    assert state.update_request_status(rid, "bar") is True
    val = state.get_request_data(rid)
    assert val.get("status") == "bar"

def test_set_and_get_status_message():
    user_id = 1001
    chat_id = 2002
    msg_id = 3003
    assert state.set_status_message(user_id, chat_id, msg_id) is True
    assert state.get_status_message(user_id, chat_id) == msg_id

def test_add_rq_job_id():
    rid = "req-job"
    state.store_request_data(rid, {"foo": "bar"})
    assert state.add_rq_job_id(rid, "jobid-xyz") is True
    data = state.get_request_data(rid)
    assert data["rq_job_id"] == "jobid-xyz"

def test_get_request_data_missing():
    assert state.get_request_data("does-not-exist") is None

def test_get_status_message_missing():
    assert state.get_status_message(99999, 88888) is None

def test_logging_on_redis_error(monkeypatch):
    # Simulate redis error and ensure False/None is returned and no exception
    monkeypatch.setattr(state, "get_redis_connection", lambda _: (_ for _ in ()).throw(Exception("fail")))
    assert state.set_pending_prompt_state(1, "req") is False
    assert state.get_pending_state(1) is None
    assert state.clear_pending_state(1) is False
    assert state.set_status_message(1, 2, 3) is False
    assert state.get_status_message(1, 2) is None
    assert state.store_request_data("x", {}) is False
    assert state.get_request_data("x") is None
    assert state.update_request_status("x", "foo") is False
    assert state.add_rq_job_id("x", "abc") is False
