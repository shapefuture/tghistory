import os
import pytest
from pydantic import ValidationError

os.environ["TELEGRAM_API_ID"] = "12345"
os.environ["TELEGRAM_API_HASH"] = "0123456789abcdef0123456789abcdef"
os.environ["TELEGRAM_SESSION_PATH"] = "/tmp/session.test"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["OUTPUT_DIR_PATH"] = "/tmp"
os.environ["LOG_LEVEL"] = "INFO"
os.environ["RQ_QUEUE_NAME"] = "default"
os.environ["LLM_API_KEY"] = "test_key"
os.environ["LLM_ENDPOINT_URL"] = "http://example.com/llm"
os.environ["LLM_MODEL_NAME"] = "dummy"
os.environ["MAX_LLM_HISTORY_TOKENS"] = "100"

from app.config import Settings

def test_valid_config_loads():
    s = Settings()
    assert s.TELEGRAM_API_ID == 12345
    assert s.TELEGRAM_API_HASH == "0123456789abcdef0123456789abcdef"

def test_invalid_telegram_api_id():
    os.environ["TELEGRAM_API_ID"] = "-123"
    with pytest.raises(ValidationError):
        Settings()
    os.environ["TELEGRAM_API_ID"] = "12345"