import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.userbot import handlers, state

@pytest.mark.asyncio
async def test_handle_message_input_prompt(monkeypatch):
    event = MagicMock()
    event.sender_id = 123
    event.raw_text = "some prompt"
    event.is_group = False
    event.is_channel = False
    event.fwd_from = None
    event.is_private = True
    event.chat_id = 555
    state.get_pending_state = lambda uid: "rid123"
    state.store_request_data = lambda rid, d: None
    state.clear_pending_state = lambda uid: None
    handlers.enqueue_processing_job = AsyncMock()
    event.respond = AsyncMock()
    state.set_status_message = lambda u, c, m: None

    await handlers.handle_message_input(event)
    event.respond.assert_awaited()

@pytest.mark.asyncio
async def test_handle_message_input_cancel(monkeypatch):
    event = MagicMock()
    event.sender_id = 42
    event.raw_text = "/cancel"
    state.get_pending_state = lambda uid: "xyz"
    state.clear_pending_state = lambda uid: None
    event.respond = AsyncMock()

    await handlers.handle_message_input(event)
    event.respond.assert_awaited()