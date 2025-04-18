import pytest
from app.worker.llm_service import truncate_history, estimate_token_count

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