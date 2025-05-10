import asyncio
import pytest
from app.userbot import results_sender

class DummyClient:
    def __init__(self):
        self.sent = []
    async def send_message(self, user_id, text):
        self.sent.append(("msg", user_id, text))
    async def send_file(self, user_id, file, caption=None):
        self.sent.append(("file", user_id, file, caption))

@pytest.mark.asyncio
async def test_send_llm_result_simple(tmp_path):
    client = DummyClient()
    await results_sender.send_llm_result(
        client,
        user_id=1,
        chat_id=2,
        job_result_dict={"summary": "short summary", "metrics": {"message_count": 10}}
    )
    assert any("msg" == x[0] for x in client.sent)

@pytest.mark.asyncio
async def test_send_llm_result_long(monkeypatch, tmp_path):
    client = DummyClient()
    longtext = "x" * 5000
    await results_sender.send_llm_result(
        client,
        user_id=1,
        chat_id=2,
        job_result_dict={"summary": longtext, "metrics": {"message_count": 10}}
    )
    assert any("msg" == x[0] for x in client.sent)

@pytest.mark.asyncio
async def test_send_llm_result_participants_file(tmp_path):
    client = DummyClient()
    pf = tmp_path / "file.txt"
    pf.write_text("hi")
    await results_sender.send_llm_result(
        client,
        user_id=1,
        chat_id=2,
        job_result_dict={"summary": "sum", "participants_file": str(pf), "metrics": {"message_count": 10}}
    )
    assert os.path.exists(str(pf)) is False

@pytest.mark.asyncio
async def test_send_llm_result_invalid(monkeypatch):
    client = DummyClient()
    await results_sender.send_llm_result(client, 1, 2, "badtype")
    assert any("msg" == x[0] for x in client.sent)

@pytest.mark.asyncio
async def test_send_failure_message_traceback(monkeypatch):
    client = DummyClient()
    await results_sender.send_failure_message(
        client, 1, 2, {"error": "fail", "traceback": "trace"*1000}
    )
    assert any("msg" == x[0] for x in client.sent)

@pytest.mark.asyncio
async def test_send_failure_message_invalid(monkeypatch):
    client = DummyClient()
    await results_sender.send_failure_message(client, 1, 2, "badtype")
    assert any("msg" == x[0] for x in client.sent)
