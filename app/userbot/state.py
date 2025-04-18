import redis
import logging
import time
from typing import Optional, Tuple, Dict, Any
from app.shared.redis_client import get_redis_connection
from app import config

# Redis Keys
# user:{user_id}:state (Hash, TTL=300s)      [pending_request_id, ...]
# request:{request_id}:data (Hash, TTL=24hr) [status, target_chat_id, custom_prompt, user_id, etc.]

USER_STATE_TTL = 300         # 5 minutes
REQUEST_DATA_TTL = 86400     # 24 hours

logger = logging.getLogger("userbot.state")

def _user_state_key(user_id: int) -> str:
    return f"user:{user_id}:state"

def _request_data_key(request_id: str) -> str:
    return f"request:{request_id}:data"

def set_pending_prompt_state(user_id: int, request_id: str):
    r = get_redis_connection(config.settings)
    try:
        k = _user_state_key(user_id)
        r.hset(k, "pending_request_id", request_id)
        r.expire(k, USER_STATE_TTL)
    except redis.exceptions.RedisError as e:
        logger.error(f"Failed to set pending prompt state: {e}")

def get_pending_state(user_id: int) -> Optional[str]:
    r = get_redis_connection(config.settings)
    try:
        k = _user_state_key(user_id)
        request_id = r.hget(k, "pending_request_id")
        if request_id:
            return request_id.decode()
        return None
    except redis.exceptions.RedisError as e:
        logger.error(f"Failed to get pending state: {e}")
        return None

def clear_pending_state(user_id: int):
    r = get_redis_connection(config.settings)
    try:
        k = _user_state_key(user_id)
        r.delete(k)
    except redis.exceptions.RedisError as e:
        logger.error(f"Failed to clear pending state: {e}")

def set_status_message(user_id: int, chat_id: int, message_id: int):
    r = get_redis_connection(config.settings)
    try:
        k = _user_state_key(user_id)
        field = f"status_message:{chat_id}"
        r.hset(k, field, message_id)
        r.expire(k, USER_STATE_TTL)
    except redis.exceptions.RedisError as e:
        logger.error(f"Failed to set status message: {e}")

def get_status_message(user_id: int, chat_id: int) -> Optional[int]:
    r = get_redis_connection(config.settings)
    try:
        k = _user_state_key(user_id)
        field = f"status_message:{chat_id}"
        msg_id = r.hget(k, field)
        if msg_id:
            return int(msg_id)
        return None
    except redis.exceptions.RedisError as e:
        logger.error(f"Failed to get status message: {e}")
        return None

def store_request_data(request_id: str, data: Dict[str, Any]):
    r = get_redis_connection(config.settings)
    try:
        k = _request_data_key(request_id)
        r.hset(k, mapping={k: str(v) for k, v in data.items()})
        r.expire(k, REQUEST_DATA_TTL)
    except redis.exceptions.RedisError as e:
        logger.error(f"Failed to store request data: {e}")

def update_request_status(request_id: str, status: str):
    r = get_redis_connection(config.settings)
    try:
        k = _request_data_key(request_id)
        r.hset(k, "status", status)
        r.expire(k, REQUEST_DATA_TTL)
    except redis.exceptions.RedisError as e:
        logger.error(f"Failed to update request status: {e}")

def get_request_data(request_id: str) -> Optional[Dict[str, str]]:
    r = get_redis_connection(config.settings)
    try:
        k = _request_data_key(request_id)
        d = r.hgetall(k)
        if d:
            return {k.decode(): v.decode() for k, v in d.items()}
        return None
    except redis.exceptions.RedisError as e:
        logger.error(f"Failed to get request data: {e}")
        return None

def add_rq_job_id(request_id: str, rq_job_id: str):
    r = get_redis_connection(config.settings)
    try:
        k = _request_data_key(request_id)
        r.hset(k, "rq_job_id", rq_job_id)
        r.expire(k, REQUEST_DATA_TTL)
    except redis.exceptions.RedisError as e:
        logger.error(f"Failed to add rq_job_id: {e}")