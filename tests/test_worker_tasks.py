from unittest.mock import patch, MagicMock

from app.worker import tasks

def test_task_failure(monkeypatch):
    # Force error in Telethon connect to trigger failure path
    monkeypatch.setattr(tasks, "TelegramClient", MagicMock(side_effect=Exception("fail")))
    result = tasks.extract_and_summarize_data(1, "/fake/path", 2, "ridX", "prompt here")
    assert result["status"] == "FAILURE"

def test_task_no_history(monkeypatch):
    # Patch client to return empty history
    fakecli = MagicMock()
    fakecli.is_user_authorized.return_value = True
    fakecli.iter_messages.return_value = []
    fakecli.get_entity.return_value = MagicMock(participants_count=0)
    fakecli.connect.return_value = True

    monkeypatch.setattr(tasks, "TelegramClient", MagicMock(return_value=fakecli))
    result = tasks.extract_and_summarize_data(1, "/fake/path", 2, "ridX", "prompt here")
    assert result["status"] == "FAILURE"