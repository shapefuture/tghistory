import pytest
from app.worker.llm_service import truncate_history, estimate_token_count, get_llm_summary
from app.config import Settings

@pytest.mark.asyncio
async def test_llm_summary_fallback(monkeypatch):
    # LLM_API_KEY is None, should trigger fallback string
    settings = Settings(
        TELEGRAM_API_ID=123,
        TELEGRAM_API_HASH="a"*32,
        TELEGRAM_SESSION_PATH="session.session",
        REDIS_URL="redis://localhost:6379",
        LLM_API_KEY=None,
        LLM_ENDPOINT_URL=None,
    )
    result = await get_llm_summary("test prompt", "test history", settings)
    assert "[LLM NOT CONFIGURED]" in result

def test_estimate_token_count():
    txt = "hello world this is a test" * 100
    tokens = estimate_token_count(txt)
    assert isinstance(tokens, int)
    assert tokens > 0

def test_truncate_history_truncates():
    longtxt = "one two " * 3000
    truncated = truncate_history(longtxt, max_tokens=1000)
    assert "[TRUNCATED]" in truncated
    assert len(truncated.split()) <= 2005  # 2*keep (1000*2)+a few for join
