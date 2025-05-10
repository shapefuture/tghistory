from pydantic import BaseModel, ValidationError, validator
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger("schemas")

class TaskStatusSchema(BaseModel):
    chat_id: Optional[int]
    status: Optional[str]
    progress: Optional[int]
    participants_file: Optional[str]
    summary: Optional[str]
    error: Optional[str]

    @validator('status')
    def validate_status(cls, v):
        logger.debug(f"Validating status: {v}")
        allowed = {"PENDING_PROMPT", "QUEUED", "STARTED", "EXTRACTING_HISTORY", "PROGRESS", "EXTRACTING_PARTICIPANTS", "WAITING", "CALLING_LLM", "SUCCESS", "FAILED"}
        if v and v not in allowed:
            logger.error(f"Invalid status value: {v}")
            raise ValueError(f"Invalid status: {v}")
        return v

    @validator('progress')
    def validate_progress(cls, v):
        logger.debug(f"Validating progress: {v}")
        if v is not None and (not isinstance(v, int) or v < 0):
            logger.error(f"Invalid progress value: {v}")
            raise ValueError("progress must be a non-negative integer")
        return v

class ProcessingRequestSchema(BaseModel):
    request_id: Optional[str]
    user_id: Optional[int]
    status: Optional[str]
    target_chat_id: Optional[int]
    custom_prompt: Optional[str]
    tasks: Optional[List[TaskStatusSchema]] = None

    @validator('user_id', 'target_chat_id', pre=True)
    def validate_ints(cls, v, field):
        logger.debug(f"Validating {field.name}: {v}")
        if v is not None:
            try:
                return int(v)
            except Exception as e:
                logger.error(f"Invalid {field.name} value: {v} ({e})")
                raise
        return v

    @validator('status')
    def validate_status(cls, v):
        logger.debug(f"Validating request status: {v}")
        allowed = {"PENDING_PROMPT", "QUEUED", "STARTED", "EXTRACTING_HISTORY", "PROGRESS", "EXTRACTING_PARTICIPANTS", "WAITING", "CALLING_LLM", "SUCCESS", "FAILED"}
        if v and v not in allowed:
            logger.error(f"Invalid request status value: {v}")
            raise ValueError(f"Invalid status: {v}")
        return v

    @validator('tasks', pre=True, always=True)
    def validate_tasks(cls, v):
        logger.debug(f"Validating tasks: {v}")
        if v is None:
            return []
        if isinstance(v, list):
            return [TaskStatusSchema(**item) if isinstance(item, dict) else item for item in v]
        logger.error(f"tasks field must be a list, got {type(v)}")
        raise ValueError("tasks must be a list of TaskStatusSchema or dicts")

def safe_parse_model(model_cls, data: Dict[str, Any]):
    logger.debug(f"safe_parse_model called: model_cls={model_cls.__name__}, data_keys={list(data.keys())}")
    try:
        obj = model_cls(**data)
        logger.info(f"{model_cls.__name__} instantiated successfully")
        return obj
    except ValidationError as ve:
        logger.error(f"{model_cls.__name__} validation error: {ve}")
        return None
    except Exception as e:
        logger.error(f"Failed to instantiate {model_cls.__name__}: {e}", exc_info=True)
        return None
