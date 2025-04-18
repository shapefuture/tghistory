import os
import sys
from typing import Optional

from pydantic import BaseSettings, validator, ValidationError
import logging

class Settings(BaseSettings):
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_SESSION_PATH: str
    REDIS_URL: str
    OUTPUT_DIR_PATH: str
    LOG_LEVEL: str = "INFO"
    RQ_QUEUE_NAME: str = "default"
    LLM_API_KEY: str
    LLM_ENDPOINT_URL: Optional[str] = None
    LLM_MODEL_NAME: Optional[str] = None
    MAX_LLM_HISTORY_TOKENS: int = 3000

    @validator("TELEGRAM_API_ID")
    def validate_telegram_id(cls, v):
        if not isinstance(v, int) or v < 0:
            raise ValueError("TELEGRAM_API_ID must be a positive integer")
        return v

    @validator("TELEGRAM_API_HASH")
    def validate_telegram_hash(cls, v):
        if not (isinstance(v, str) and len(v) == 32):
            raise ValueError("TELEGRAM_API_HASH must be a 32-character string")
        return v

    @validator("TELEGRAM_SESSION_PATH", "OUTPUT_DIR_PATH")
    def validate_path_exists(cls, v):
        if not os.path.exists(v):
            raise ValueError(f"Path does not exist: {v}")
        if not os.access(v, os.W_OK):
            raise ValueError(f"Path is not writable: {v}")
        return v

    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must start with redis://")
        return v

    @validator("LLM_API_KEY")
    def validate_llm_key(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("LLM_API_KEY must be a nonempty string")
        return v

# Load settings at import for easy global import
try:
    settings = Settings(_env_file=os.getenv("ENV_FILE", ".env"))
except ValidationError as exc:
    logging.basicConfig(level="ERROR")
    logging.error(
        f"❌ [Config Validation] Environment configuration error(s):\n{exc}"
    )
    sys.exit(1)