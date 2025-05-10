import re
import logging

logger = logging.getLogger("worker.utils")

def clean_message_text(text: str) -> str:
    """
    Removes zero-width chars and excess whitespace, logs before/after.
    """
    logger.debug(f"[ENTRY] clean_message_text(text-len={len(text) if text else 0})")
    try:
        cleaned = re.sub(r"[\u200b-\u200d]", "", text)
        cleaned = re.sub(r"\s+", " ", cleaned)
        result = cleaned.strip()
        logger.debug(f"[EXIT] clean_message_text: output-len={len(result)}")
        return result
    except Exception as e:
        logger.error(f"[ERROR] Error cleaning message text: {e}", exc_info=True)
        return text
