import logging
import traceback
from typing import Any, Dict, Optional

from app.shared.redis_client import get_redis_connection
from app import config

logger = logging.getLogger("userbot.state")

USER_STATE_KEY = "user:{user_id}:state"
USER_STATUS_MESSAGE_KEY = "user:{user_id}:status:{chat_id}"
REQUEST_DATA_KEY = "request:{request_id}:data"

USER_STATE_TTL = 60 * 5
REQUEST_DATA_TTL = 60 * 60 * 24

def set_pending_prompt_state(user_id: int, request_id: str) -> bool:
    logger.debug(f"[ENTRY] set_pending_prompt_state(user_id={user_id}, request_id={request_id})")
    try:
        redis_conn = get_redis_connection(config.settings)
        key = USER_STATE_KEY.format(user_id=user_id)
        redis_conn.setex(key, USER_STATE_TTL, request_id)
        logger.info(f"Set pending prompt state for user_id={user_id} request_id={request_id}")
        logger.debug(f"[EXIT] set_pending_prompt_state: True")
        return True
    except Exception as e:
        logger.error(f"[ERROR] set_pending_prompt_state: {e}", exc_info=True)
        return False

def get_pending_state(user_id: int) -> Optional[str]:
    logger.debug(f"[ENTRY] get_pending_state(user_id={user_id})")
    try:
        redis_conn = get_redis_connection(config.settings)
        key = USER_STATE_KEY.format(user_id=user_id)
        value = redis_conn.get(key)
        result = value.decode() if value else None
        logger.debug(f"[EXIT] get_pending_state: {result}")
        return result
    except Exception as e:
        logger.error(f"[ERROR] get_pending_state: {e}", exc_info=True)
        return None

def clear_pending_state(user_id: int) -> bool:
    logger.debug(f"[ENTRY] clear_pending_state(user_id={user_id})")
    try:
        redis_conn = get_redis_connection(config.settings)
        key = USER_STATE_KEY.format(user_id=user_id)
        redis_conn.delete(key)
        logger.info(f"Cleared pending prompt state for user_id={user_id}")
        logger.debug(f"[EXIT] clear_pending_state: True")
        return True
    except Exception as e:
        logger.error(f"[ERROR] clear_pending_state: {e}", exc_info=True)
        return False

def set_status_message(user_id: int, chat_id: int, message_id: int) -> bool:
    logger.debug(f"[ENTRY] set_status_message(user_id={user_id}, chat_id={chat_id}, message_id={message_id})")
    try:
        redis_conn = get_redis_connection(config.settings)
        key = USER_STATUS_MESSAGE_KEY.format(user_id=user_id, chat_id=chat_id)
        redis_conn.setex(key, USER_STATE_TTL, message_id)
        logger.info(f"Set status message for user_id={user_id}, chat_id={chat_id}, message_id={message_id}")
        logger.debug("[EXIT] set_status_message: True")
        return True
    except Exception as e:
        logger.error(f"[ERROR] set_status_message: {e}", exc_info=True)
        return False

def get_status_message(user_id: int, chat_id: int) -> Optional[int]:
    logger.debug(f"[ENTRY] get_status_message(user_id={user_id}, chat_id={chat_id})")
    try:
        redis_conn = get_redis_connection(config.settings)
        key = USER_STATUS_MESSAGE_KEY.format(user_id=user_id, chat_id=chat_id)
        value = redis_conn.get(key)
        result = int(value.decode()) if value else None
        logger.debug(f"[EXIT] get_status_message: {result}")
        return result
    except Exception as e:
        logger.error(f"[ERROR] get_status_message: {e}", exc_info=True)
        return None

def store_request_data(request_id: str, data: Dict[str, Any]) -> bool:
    logger.debug(f"[ENTRY] store_request_data(request_id={request_id}, data_keys={list(data.keys())})")
    try:
        redis_conn = get_redis_connection(config.settings)
        key = REQUEST_DATA_KEY.format(request_id=request_id)
        # Make sure all values are strings
        str_data = {k: str(v) for k, v in data.items()}
        redis_conn.hset(key, mapping=str_data)
        redis_conn.expire(key, REQUEST_DATA_TTL)
        logger.info(f"Stored request data for request_id={request_id}")
        logger.debug(f"[EXIT] store_request_data: True")
        return True
    except Exception as e:
        logger.error(f"[ERROR] store_request_data: {e}", exc_info=True)
        return False

def get_request_data(request_id: str) -> Optional[Dict[str, Any]]:
    logger.debug(f"[ENTRY] get_request_data(request_id={request_id})")
    try:
        redis_conn = get_redis_connection(config.settings)
        key = REQUEST_DATA_KEY.format(request_id=request_id)
        data = redis_conn.hgetall(key)
        if not data:
            logger.warning(f"No request data found for request_id={request_id}")
            logger.debug(f"[EXIT] get_request_data: None")
            return None
        decoded = {k.decode(): v.decode() for k, v in data.items()}
        logger.debug(f"[EXIT] get_request_data: keys={list(decoded.keys())}")
        return decoded
    except Exception as e:
        logger.error(f"[ERROR] get_request_data: {e}", exc_info=True)
        return None

def update_request_status(request_id: str, status: str) -> bool:
    logger.debug(f"[ENTRY] update_request_status(request_id={request_id}, status={status})")
    try:
        redis_conn = get_redis_connection(config.settings)
        key = REQUEST_DATA_KEY.format(request_id=request_id)
        redis_conn.hset(key, "status", status)
        logger.info(f"Updated request status for request_id={request_id} to {status}")
        logger.debug("[EXIT] update_request_status: True")
        return True
    except Exception as e:
        logger.error(f"[ERROR] update_request_status: {e}", exc_info=True)
        return False

def add_rq_job_id(request_id: str, rq_job_id: str) -> bool:
    logger.debug(f"[ENTRY] add_rq_job_id(request_id={request_id}, rq_job_id={rq_job_id})")
    try:
        redis_conn = get_redis_connection(config.settings)
        key = REQUEST_DATA_KEY.format(request_id=request_id)
        redis_conn.hset(key, "rq_job_id", rq_job_id)
        logger.info(f"Added rq_job_id to request_id={request_id}: {rq_job_id}")
        logger.debug("[EXIT] add_rq_job_id: True")
        return True
    except Exception as e:
        logger.error(f"[ERROR] add_rq_job_id: {e}", exc_info=True)
        return False
