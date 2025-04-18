import pytest
import asyncio

from app.userbot import results_sender

class DummyClient:
    def __init__(self):
        self.sent = []

    async def send_message(self, uid, text):
        self.sent.append(("msg", uid, text))

    async def send_file(self, uid, path, caption=None):
        self.sent.append(("file", uid, path, caption))

@pytest.mark.asyncio
async def test_send_llm_result_basic(tmp_path):
    client = DummyClient()
    job_result = {"summary": "hi!"}
    await results_sender.send_llm_result(client, 1, 2, job_result)
    assert any(x[0]=="msg" and x[2]=="hi!" for x in client.sent)

@pytest.mark.asyncio
async def test_send_llm_result_with_participants(tmp_path):
    # Make a participants file
    file_path = tmp_path / "p.txt"
    file_path.write_text("participants!")
    job_result = {"summary": "hi", "participants_file": str(file_path)}
    client = DummyClient()
    await results_sender.send_llm_result(client, 1, 2, job_result)
    assert any(x[0]=="file" and x[2]==str(file_path) for x in client.sent)
    # File should get deleted
    assert not file_path.exists()

@pytest.mark.asyncio
async def test_send_failure_message():
    client = DummyClient()
    job_result = {"error": "myfail"}
    await results_sender.send_failure_message(client, 1, 3, job_result)
    assert any(x[0]=="msg" and "myfail" in x[2] for x in client.sent)