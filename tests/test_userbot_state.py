import fakeredis
import pytest
from app.userbot import state

@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr(state, "get_redis_connection", lambda _: fake)
    yield

def test_pending_prompt_state():
    user_id = 101
    req_id = "abc123"
    state.set_pending_prompt_state(user_id, req_id)
    found = state.get_pending_state(user_id)
    assert found == req_id
    state.clear_pending_state(user_id)
    found2 = state.get_pending_state(user_id)
    assert found2 is None

def test_store_request_data():
    req_id = "qid"
    data = {"status": "PENDING", "foo": "bar"}
    state.store_request_data(req_id, data)
    d2 = state.get_request_data(req_id)
    assert d2["foo"] == "bar"
    state.update_request_status(req_id, "QUEUED")
    d3 = state.get_request_data(req_id)
    assert d3["status"] == "QUEUED"