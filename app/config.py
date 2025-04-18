import os
import sys
from typing import Optional

from pydantic import BaseSettings, validator, ValidationError
import logging

class Settings(BaseSettings):
    # Support both new and old naming patterns for backward compatibility
    TELEGRAM_API_ID: Optional[int] = None
    API_ID: Optional[int] = None
    
    TELEGRAM_API_HASH: Optional[str] = None
    API_HASH: Optional[str] = None
    
    TELEGRAM_SESSION_PATH: Optional[str] = None
    SESSION: Optional[str] = None
    
    REDIS_URL: Optional[str] = None
    REDIS_URI: Optional[str] = None
    
    OUTPUT_DIR_PATH: str = "/data/output"
    LOG_LEVEL: str = "INFO"
    RQ_QUEUE_NAME: str = "default"
    
    # Make LLM-related config optional
    LLM_API_KEY: Optional[str] = None
    LLM_ENDPOINT_URL: Optional[str] = None
    LLM_MODEL_NAME: Optional[str] = None
    MAX_LLM_HISTORY_TOKENS: int = 3000
    
    # Optional backward compatibility for other env vars
    LOG_CHANNEL: Optional[str] = None
    BOT_TOKEN: Optional[str] = None

    def __init__(self, **data):
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

    @validator("TELEGRAM_API_ID", pre=True)
    def validate_telegram_id(cls, v):
        if v is None:
            return None
        if not isinstance(v, int) and v is not None:
            try:
                v = int(v)
            except (ValueError, TypeError):
                raise ValueError("TELEGRAM_API_ID must be a positive integer")
        if v is not None and v < 0:
            raise ValueError("TELEGRAM_API_ID must be a positive integer")
        return v

    @validator("TELEGRAM_API_HASH")
    def validate_telegram_hash(cls, v):
        if v is None:
            return None
        if not (isinstance(v, str) and len(v) == 32):
            raise ValueError("TELEGRAM_API_HASH must be a 32-character string")
        return v

    @validator("TELEGRAM_SESSION_PATH", "OUTPUT_DIR_PATH")
    def validate_path_exists(cls, v):
        if v is None:
            return None
            
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(v), exist_ok=True)
        
        # Only check writability for existing files
        if os.path.exists(v) and not os.access(v, os.W_OK):
            raise ValueError(f"Path exists but is not writable: {v}")
        return v

    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        if v is None:
            return None
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must start with redis://")
        return v

    @validator("LLM_API_KEY")
    def validate_llm_key(cls, v):
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("LLM_API_KEY must be a string")
        return v
        
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Load settings at import for easy global import
try:
    settings = Settings(_env_file=os.getenv("ENV_FILE", ".env"))
    
    # Validate required fields after fallbacks applied
    if settings.TELEGRAM_API_ID is None:
        raise ValidationError("TELEGRAM_API_ID or API_ID is required")
    if settings.TELEGRAM_API_HASH is None:
        raise ValidationError("TELEGRAM_API_HASH or API_HASH is required")
    if settings.TELEGRAM_SESSION_PATH is None:
        raise ValidationError("TELEGRAM_SESSION_PATH or SESSION is required")
    if settings.REDIS_URL is None:
        raise ValidationError("REDIS_URL or REDIS_URI is required")
        
except Exception as exc:
    logging.basicConfig(level="ERROR")
    logging.error(
        f"❌ [Config Validation] Environment configuration error(s):\n{exc}"
    )
    sys.exit(1)