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
    state.set_pending_prompt_state(user_id, request_id)
    assert state.get_pending_state(user_id) == request_id
    state.clear_pending_state(user_id)
    assert state.get_pending_state(user_id) is None

def test_store_request_data():
    rid = "req2"
    d = {"foo": "bar", "num": "42"}
    state.store_request_data(rid, d)
    val = state.get_request_data(rid)
    assert isinstance(val, dict)
    assert val.get("foo") == "bar"
    assert val.get("num") == "42"

def test_update_request_status():
    rid = "req3"
    state.store_request_data(rid, {"status": "foo"})
    state.update_request_status(rid, "bar")
    val = state.get_request_data(rid)
    assert val.get("status") == "bar"