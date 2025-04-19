import logging
import time
from typing import Optional
import httpx
import json
import traceback

from app import config

logger = logging.getLogger("worker.llm_service")

def estimate_token_count(text: str) -> int:
    """
    Estimate the number of tokens in a text using a simple heuristic
    
    Args:
        text: Input text
        
    Returns:
        int: Estimated token count
    """
    logger.debug(f"Estimating token count for text of length {len(text)}")
    
    try:
        # Simple heuristic; you can use tiktoken if wanted
        # GPT-3 token/word is ~0.75, so 4/3 * words
        word_count = len(text.split())
        estimated_tokens = int(1.33 * word_count)
        
        logger.debug(f"Token estimation: words={word_count}, estimated_tokens={estimated_tokens}")
        return estimated_tokens
    except Exception as e:
        logger.exception(f"Error estimating token count: {e}")
        # Return a conservative estimate to prevent errors
        return len(text) // 3

def truncate_history(history_text: str, max_tokens: int) -> str:
    """
    Truncate text to fit within token limits while preserving context
    
    Args:
        history_text: Full history text
        max_tokens: Maximum tokens allowed
        
    Returns:
        str: Truncated text
    """
    logger.debug(f"Truncating history: text_length={len(history_text)}, max_tokens={max_tokens}")
    
    try:
        words = history_text.split()
        word_count = len(words)
        logger.debug(f"History word count: {word_count}")
        
        est_tokens = estimate_token_count(history_text)
        logger.debug(f"Estimated token count: {est_tokens}")
        
        if est_tokens <= max_tokens:
            logger.debug("History fits within token limit, no truncation needed")
            return history_text
            
        # Keep half from beginning, half from end
        keep_tokens = max_tokens // 2
        keep_words = int(keep_tokens / 1.33)  # Convert back to approximate word count
        
        logger.info(f"Truncating history: original_tokens={est_tokens}, keeping={max_tokens} tokens (~{keep_words*2} words)")
        
        head = words[:keep_words]
        tail = words[-keep_words:]
        
        truncated_text = " ".join(head) + " ... [TRUNCATED] ... " + " ".join(tail)
        truncated_token_count = estimate_token_count(truncated_text)
        
        logger.info(f"History truncated: original_tokens={est_tokens}, truncated_tokens={truncated_token_count}")
        return truncated_text
    except Exception as e:
        logger.exception(f"Error truncating history: {e}")
        # In case of error, make a best effort to truncate
        try:
            # Simple character-based truncation as fallback
            if len(history_text) > max_tokens * 4:  # Rough character estimate
                half_size = (max_tokens * 4) // 2
                truncated = history_text[:half_size] + " ... [TRUNCATED] ... " + history_text[-half_size:]
                logger.warning(f"Used fallback truncation method after error: {e}")
                return truncated
            return history_text
        except Exception as fallback_error:
            logger.error(f"Fallback truncation also failed: {fallback_error}")
            return history_text

async def get_llm_summary(prompt: str, history_text: str, settings: config.Settings) -> Optional[str]:
    """
    Call LLM API to generate a summary
    
    Args:
        prompt: User-provided instruction prompt
        history_text: Telegram chat history text
        settings: Application configuration
        
    Returns:
        Optional[str]: Generated summary or None on failure
    """
    start_time = time.time()
    logger.info(f"Getting LLM summary: prompt_length={len(prompt)}, history_length={len(history_text)}")
    
    # If LLM is not configured, return a fallback message
    if not settings.LLM_API_KEY or not settings.LLM_ENDPOINT_URL:
        logger.warning("LLM not configured. Using fallback message.")
        return f"[LLM NOT CONFIGURED] - Extraction completed, but summarization is not available.\n\nPrompt: {prompt}\n\nConfigure LLM_API_KEY and LLM_ENDPOINT_URL to enable summarization."
    
    try:
        # Truncate history to fit token limit
        max_tokens = settings.MAX_LLM_HISTORY_TOKENS
        logger.debug(f"Truncating history to max {max_tokens} tokens")
        truncated_history = truncate_history(history_text, max_tokens)
        
        truncation_stats = {
            "original_length": len(history_text),
            "truncated_length": len(truncated_history),
            "estimated_original_tokens": estimate_token_count(history_text),
            "estimated_truncated_tokens": estimate_token_count(truncated_history)
        }
        logger.debug(f"Truncation stats: {truncation_stats}")

        # Prepare request
        body = {
            "prompt": prompt,
            "history": truncated_history,
            "model": settings.LLM_MODEL_NAME,
        }
        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        
        logger.debug(f"Preparing LLM API call: endpoint={settings.LLM_ENDPOINT_URL}, model={settings.LLM_MODEL_NAME}")
        
        # Make API request
        request_start_time = time.time()
        async with httpx.AsyncClient(timeout=120) as client:
            logger.debug(f"Sending HTTP request to LLM API")
            
            try:
                resp = await client.post(settings.LLM_ENDPOINT_URL, json=body, headers=headers)
                
                request_time = time.time() - request_start_time
                logger.debug(f"LLM API response received: status_code={resp.status_code}, time={request_time:.2f}s")
                
                if resp.status_code != 200:
                    logger.error(f"LLM API HTTP error {resp.status_code}: {resp.text}")
                    return f"[LLM API Error] {resp.status_code}: Unable to generate summary. Response: {resp.text[:500]}"
                    
                # Parse response
                try:
                    data = resp.json()
                    logger.debug(f"LLM API response parsed: keys={list(data.keys())}")
                except json.JSONDecodeError as json_err:
                    logger.error(f"Failed to parse LLM API response as JSON: {json_err}, response: {resp.text[:500]}")
                    return f"[LLM Response Parse Error] Unable to parse response as JSON: {str(json_err)}"
                
                # Extract summary
                summary = data.get("summary") or data.get("result")
                if not summary:
                    logger.error(f"Missing summary/result in LLM response: {data}")
                    return f"[LLM Response Error] Missing summary in response: {str(data)[:500]}"
                
                total_time = time.time() - start_time
                logger.info(f"LLM summary generated: length={len(summary)}, time={total_time:.2f}s")
                return summary
                
            except httpx.TimeoutException as e:
                logger.error(f"LLM API request timeout: {e}")
                return f"[LLM Timeout Error] Request timed out after {e.timeout}s"
                
            except httpx.RequestError as e:
                logger.error(f"HTTPX request error: {e}")
                return f"[LLM Network Error] {type(e).__name__}: {str(e)}"
    except Exception as e:
        logger.exception(f"LLM summarization exception: {e}")
        error_traceback = traceback.format_exc()
        return f"[LLM Processing Error] {type(e).__name__}: {str(e)}\n\nDetails: {error_traceback[:500]}"