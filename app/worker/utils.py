import re
import logging

logger = logging.getLogger("worker.utils")

def clean_message_text(text: str) -> str:
    """
    Fully implemented: removes zero-width chars and excess whitespace, logs before/after.
    """
    try:
        logger.debug(f"Cleaning message text, input length={len(text)}")
        cleaned = re.sub(r"[\u200b-\u200d]", "", text)
        cleaned = re.sub(r"\s+", " ", cleaned)
        result = cleaned.strip()
        logger.debug(f"Cleaned message text, output length={len(result)}")
        return result
    except Exception as e:
        logger.error(f"Error cleaning message text: {e}", exc_info=True)
        return text
