from unittest.mock import patch, MagicMock
from app.worker import tasks

def test_task_failure(monkeypatch):
    monkeypatch.setattr(tasks, "TelegramClient", MagicMock(side_effect=Exception("fail")))
    result = tasks.extract_and_summarize_data(1, "/fake/path", 2, "ridX", "prompt here")
    assert result["status"] == "FAILURE"

def test_task_no_history(monkeypatch):
    fakecli = MagicMock()
    fakecli.is_user_authorized.return_value = True
    fakecli.iter_messages.return_value = []
    fakecli.get_entity.return_value = MagicMock(participants_count=0)
    fakecli.connect.return_value = True
    monkeypatch.setattr(tasks, "TelegramClient", MagicMock(return_value=fakecli))
    result = tasks.extract_and_summarize_data(1, "/fake/path", 2, "ridX", "prompt here")
    assert result["status"] == "FAILURE"

def test_task_success(monkeypatch):
    fakecli = MagicMock()
    fakecli.is_user_authorized.return_value = True
    fakecli.iter_messages.return_value = [MagicMock(text="Hello!"), MagicMock(text="Test!")]
    fakecli.get_entity.return_value = MagicMock(participants_count=0)
    fakecli.connect.return_value = True
    def fake_disconnect(): pass
    fakecli.disconnect.side_effect = fake_disconnect
    monkeypatch.setattr(tasks, "TelegramClient", MagicMock(return_value=fakecli))
    # Patch LLM
    monkeypatch.setattr(tasks, "get_llm_summary", lambda prompt, hist, settings: "summary result")
    result = tasks.extract_and_summarize_data(1, "/fake/path", 2, "ridX", "prompt here")
    assert result["status"] == "SUCCESS"
    assert "summary" in result
