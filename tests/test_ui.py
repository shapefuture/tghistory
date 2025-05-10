import pytest
from unittest.mock import AsyncMock, patch
from app.userbot import ui

@pytest.mark.asyncio
async def test_update_status_message_success(monkeypatch):
    # Everything present, should call edit_message
    state_data = {
        "user_id": 1,
        "target_chat_id": 2,
        "status": "SUCCESS"
    }
    monkeypatch.setattr("app.userbot.state.get_request_data", lambda rid: state_data)
    monkeypatch.setattr("app.userbot.state.get_status_message", lambda u, c: 99)
    client = AsyncMock()
    await ui.update_status_message_for_request(client, "rid")
    client.edit_message.assert_awaited_with(1, 99, "✅ Status for chat 2: SUCCESS")

@pytest.mark.asyncio
async def test_update_status_message_missing_data(monkeypatch):
    monkeypatch.setattr("app.userbot.state.get_request_data", lambda rid: None)
    client = AsyncMock()
    await ui.update_status_message_for_request(client, "rid")
    assert not client.edit_message.await_count

@pytest.mark.asyncio
async def test_update_status_message_missing_fields(monkeypatch):
    monkeypatch.setattr("app.userbot.state.get_request_data", lambda rid: {"user_id": None, "target_chat_id": None, "status": None})
    client = AsyncMock()
    await ui.update_status_message_for_request(client, "rid")
    assert not client.edit_message.await_count

@pytest.mark.asyncio
async def test_update_status_message_no_msg_id(monkeypatch):
    state_data = {
        "user_id": 1,
        "target_chat_id": 2,
        "status": "SUCCESS"
    }
    monkeypatch.setattr("app.userbot.state.get_request_data", lambda rid: state_data)
    monkeypatch.setattr("app.userbot.state.get_status_message", lambda u, c: None)
    client = AsyncMock()
    await ui.update_status_message_for_request(client, "rid")
    assert not client.edit_message.await_count

@pytest.mark.asyncio
async def test_update_status_message_edit_error(monkeypatch):
    state_data = {
        "user_id": 1,
        "target_chat_id": 2,
        "status": "SUCCESS"
    }
    monkeypatch.setattr("app.userbot.state.get_request_data", lambda rid: state_data)
    monkeypatch.setattr("app.userbot.state.get_status_message", lambda u, c: 99)
    client = AsyncMock()
    client.edit_message.side_effect = Exception("fail!")
    await ui.update_status_message_for_request(client, "rid")
    assert client.edit_message.await_count == 1
