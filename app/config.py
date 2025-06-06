import os
import sys
from typing import Optional

from pydantic import BaseSettings, validator, ValidationError
import logging
import traceback

logger = logging.getLogger("config")

class Settings(BaseSettings):
    TELEGRAM_API_ID: Optional[int] = None
    TELEGRAM_API_HASH: Optional[str] = None
    TELEGRAM_SESSION_PATH: Optional[str] = None
    REDIS_URL: Optional[str] = None
    OUTPUT_DIR_PATH: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    RQ_QUEUE_NAME: str = "default"
    LLM_API_KEY: Optional[str] = None
    LLM_ENDPOINT_URL: Optional[str] = None
    LLM_MODEL_NAME: Optional[str] = None
    MAX_LLM_HISTORY_TOKENS: int = 3000

    API_ID: Optional[int] = None
    API_HASH: Optional[str] = None
    SESSION: Optional[str] = None
    REDIS_URI: Optional[str] = None

    def __init__(self, **data):
        logger.debug(f"[ENTRY] Settings.__init__ with data keys={list(data.keys())}")
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
            logger.debug(f"[EXIT] Settings.__init__ OK")
        except Exception as e:
            logger.error(f"[ERROR] Settings init error: {e}\n{traceback.format_exc()}")
            raise

    @validator("TELEGRAM_API_ID", pre=True)
    def validate_telegram_id(cls, v):
        logger.debug(f"[ENTRY] validate_telegram_id: {v}")
        try:
            if v is None:
                return None
            if not isinstance(v, int) and v is not None:
                v = int(v)
            if v is not None and v < 0:
                logger.error(f"TELEGRAM_API_ID must be positive: {v}")
                raise ValueError("TELEGRAM_API_ID must be a positive integer")
            logger.debug(f"[EXIT] validate_telegram_id: {v}")
            return v
        except Exception as e:
            logger.error(f"[ERROR] TELEGRAM_API_ID validation error: {e}")
            raise

    @validator("TELEGRAM_API_HASH")
    def validate_telegram_hash(cls, v):
        logger.debug(f"[ENTRY] validate_telegram_hash: {v}")
        try:
            if v is None:
                return None
            if not (isinstance(v, str) and len(v) == 32):
                logger.error(f"TELEGRAM_API_HASH must be a 32-character string: {v}")
                raise ValueError("TELEGRAM_API_HASH must be a 32-character string")
            logger.debug(f"[EXIT] validate_telegram_hash: {v}")
            return v
        except Exception as e:
            logger.error(f"[ERROR] TELEGRAM_API_HASH validation error: {e}")
            raise

    @validator("TELEGRAM_SESSION_PATH", "OUTPUT_DIR_PATH")
    def validate_path_exists(cls, v):
        logger.debug(f"[ENTRY] validate_path_exists: {v}")
        try:
            if v is None:
                return None
            os.makedirs(os.path.dirname(v), exist_ok=True)
            if os.path.exists(v) and not os.access(v, os.W_OK):
                logger.error(f"Path exists but is not writable: {v}")
                raise ValueError(f"Path exists but is not writable: {v}")
            logger.debug(f"[EXIT] validate_path_exists: {v}")
            return v
        except Exception as e:
            logger.error(f"[ERROR] Path validation error for {v}: {e}")
            raise

    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        logger.debug(f"[ENTRY] validate_redis_url: {v}")
        try:
            if v is None:
                return None
            if not v.startswith("redis://"):
                logger.error(f"REDIS_URL must start with redis://: {v}")
                raise ValueError("REDIS_URL must start with redis://")
            logger.debug(f"[EXIT] validate_redis_url: {v}")
            return v
        except Exception as e:
            logger.error(f"[ERROR] REDIS_URL validation error: {e}")
            raise

    @validator("LLM_API_KEY")
    def validate_llm_key(cls, v):
        logger.debug(f"[ENTRY] validate_llm_key: {v}")
        try:
            if v is None:
                return None
            if not isinstance(v, str):
                logger.error(f"LLM_API_KEY must be a string: {v}")
                raise ValueError("LLM_API_KEY must be a string")
            logger.debug(f"[EXIT] validate_llm_key: {v}")
            return v
        except Exception as e:
            logger.error(f"[ERROR] LLM_API_KEY validation error: {e}")
            raise

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

try:
    logger.debug("[ENTRY] Loading application settings from .env")
    settings = Settings(_env_file=os.getenv("ENV_FILE", ".env"))
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
        logger.error(f"Missing required settings: {', '.join(missing)}")
        raise ValidationError(f"Missing required settings: {', '.join(missing)}")
    logger.info("Application settings loaded and validated successfully")
    logger.debug("[EXIT] Settings loaded OK")
except Exception as exc:
    logging.basicConfig(level="ERROR")
    logger.error(f"❌ [Config Validation] Environment configuration error(s):\n{exc}\n{traceback.format_exc()}")
    sys.exit(1)
