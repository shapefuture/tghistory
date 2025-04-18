import logging
from typing import Optional
import httpx

from app import config

logger = logging.getLogger("worker.llm_service")

def estimate_token_count(text: str) -> int:
    # Simple heuristic; you can use tiktoken if added
    # GPT-3 token/word is ~0.75, so 4/3 * words
    return int(1.33 * len(text.split()))

def truncate_history(history_text: str, max_tokens: int) -> str:
    words = history_text.split()
    est_tokens = estimate_token_count(history_text)
    if est_tokens <= max_tokens:
        return history_text
    keep_tokens = max_tokens // 2
    head = words[:keep_tokens]
    tail = words[-keep_tokens:]
    logger.warning("LLM history truncated for token limit.")
    return " ".join(head) + " ... [TRUNCATED] ... " + " ".join(tail)

async def get_llm_summary(prompt: str, history_text: str, settings: config.Settings) -> Optional[str]:
    # If LLM is not configured, return a fallback message
    if not settings.LLM_API_KEY or not settings.LLM_ENDPOINT_URL:
        logger.warning("LLM not configured. Using fallback message.")
        return f"[LLM NOT CONFIGURED] - Extraction completed, but summarization is not available.\n\nPrompt: {prompt}\n\nConfigure LLM_API_KEY and LLM_ENDPOINT_URL to enable summarization."
    
    max_tokens = settings.MAX_LLM_HISTORY_TOKENS
    truncated_history = truncate_history(history_text, max_tokens)

    body = {
        "prompt": prompt,
        "history": truncated_history,
        "model": settings.LLM_MODEL_NAME,
    }
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(settings.LLM_ENDPOINT_URL, json=body, headers=headers)
            if resp.status_code != 200:
                logger.error(f"LLM API HTTP error {resp.status_code}: {resp.text}")
                return f"[LLM API Error] {resp.status_code}: Unable to generate summary."
            data = resp.json()
            summary = data.get("summary") or data.get("result")
            if not summary:
                logger.error(f"Missing summary/result in LLM response: {data}")
                return f"[LLM Response Error] Missing summary in response."
            return summary
    except httpx.RequestError as e:
        logger.error(f"HTTPX request error: {e}")
        return f"[LLM Network Error] {type(e).__name__}: {str(e)}"
    except Exception as e:
        logger.exception(f"LLM summarization exception: {e}")
        return f"[LLM Processing Error] {type(e).__name__}: {str(e)}"