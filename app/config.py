import os
import sys
from typing import Optional

from pydantic import BaseSettings, validator, ValidationError
import logging
import traceback

logger = logging.getLogger("config")

class Settings(BaseSettings):
    # ... (fields unchanged for brevity) ...

    def __init__(self, **data):
        logger.debug("Initializing Settings with environment data (sensitive values hidden)")
        try:
            super().__init__(**data)
            # Apply backward compatibility
            if self.TELEGRAM_API_ID is None and self.API_ID is not None:
                self.TELEGRAM_API_ID = self.API_ID
            if self.TELEGRAM_API_HASH is None and self.API_HASH is not None:
                self.TELEGRAM_API_HASH = self.API_HASH
            if self.TELEGRAM_SESSION_PATH is None and self.SESSION is not None:
                self.TELEGRAM_SESSION_PATH = self.SESSION
            if self.REDIS_URL is None and self.REDIS_URI is not None:
                self.REDIS_URL = self.REDIS_URI
            logger.info("Settings initialized successfully")
        except Exception as e:
            logger.error(f"Settings init error: {e}\n{traceback.format_exc()}")
            raise

    # Validators: all with try/except, log before raise
    @validator("TELEGRAM_API_ID", pre=True)
    def validate_telegram_id(cls, v):
        try:
            if v is None:
                return None
            if not isinstance(v, int) and v is not None:
                v = int(v)
            if v is not None and v < 0:
                raise ValueError("TELEGRAM_API_ID must be a positive integer")
            return v
        except Exception as e:
            logger.error(f"TELEGRAM_API_ID validation error: {e}")
            raise

    @validator("TELEGRAM_API_HASH")
    def validate_telegram_hash(cls, v):
        try:
            if v is None:
                return None
            if not (isinstance(v, str) and len(v) == 32):
                raise ValueError("TELEGRAM_API_HASH must be a 32-character string")
            return v
        except Exception as e:
            logger.error(f"TELEGRAM_API_HASH validation error: {e}")
            raise

    @validator("TELEGRAM_SESSION_PATH", "OUTPUT_DIR_PATH")
    def validate_path_exists(cls, v):
        try:
            if v is None:
                return None
            os.makedirs(os.path.dirname(v), exist_ok=True)
            if os.path.exists(v) and not os.access(v, os.W_OK):
                raise ValueError(f"Path exists but is not writable: {v}")
            return v
        except Exception as e:
            logger.error(f"Path validation error for {v}: {e}")
            raise

    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        try:
            if v is None:
                return None
            if not v.startswith("redis://"):
                raise ValueError("REDIS_URL must start with redis://")
            return v
        except Exception as e:
            logger.error(f"REDIS_URL validation error: {e}")
            raise

    @validator("LLM_API_KEY")
    def validate_llm_key(cls, v):
        try:
            if v is None:
                return None
            if not isinstance(v, str):
                raise ValueError("LLM_API_KEY must be a string")
            return v
        except Exception as e:
            logger.error(f"LLM_API_KEY validation error: {e}")
            raise

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

try:
    logger.debug("Loading application settings from .env")
    settings = Settings(_env_file=os.getenv("ENV_FILE", ".env"))
    # Validate required fields after fallbacks applied
    missing = []
    if settings.TELEGRAM_API_ID is None:
        missing.append("TELEGRAM_API_ID or API_ID")
    if settings.TELEGRAM_API_HASH is None:
        missing.append("TELEGRAM_API_HASH or API_HASH")
    if settings.TELEGRAM_SESSION_PATH is None:
        missing.append("TELEGRAM_SESSION_PATH or SESSION")
    if settings.REDIS_URL is None:
        missing.append("REDIS_URL or REDIS_URI")
    if missing:
        raise ValidationError(f"Missing required settings: {', '.join(missing)}")
    logger.info("Application settings loaded and validated successfully")
except Exception as exc:
    logging.basicConfig(level="ERROR")
    logging.error(f"❌ [Config Validation] Environment configuration error(s):\n{exc}\n{traceback.format_exc()}")
    sys.exit(1)
