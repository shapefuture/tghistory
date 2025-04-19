import re

def clean_message_text(text: str) -> str:
    # Remove telegram artifacts, zero-width, excessive whitespace
    cleaned = re.sub(r"[\u200b-\u200d]", "", text)   # Zero-width
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()