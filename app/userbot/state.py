import redis
import logging
import time
import traceback
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
    """Generate Redis key for user state"""
    try:
        return f"user:{user_id}:state"
    except Exception as e:
        logger.error(f"Error generating user state key for user_id={user_id}: {e}")
        # This is a critical utility function, so we re-raise to prevent silent failures
        raise

def _request_data_key(request_id: str) -> str:
    """Generate Redis key for request data"""
    try:
        return f"request:{request_id}:data"
    except Exception as e:
        logger.error(f"Error generating request data key for request_id={request_id}: {e}")
        # This is a critical utility function, so we re-raise to prevent silent failures
        raise

def set_pending_prompt_state(user_id: int, request_id: str):
    """
    Store pending prompt state for a user in Redis
    
    Args:
        user_id: Telegram user ID
        request_id: Request ID awaiting prompt
    """
    logger.debug(f"Setting pending prompt state: user_id={user_id}, request_id={request_id}")
    
    try:
        r = get_redis_connection(config.settings)
        k = _user_state_key(user_id)
        
        # Store state and set TTL
        logger.debug(f"Setting Redis hash: key={k}, field=pending_request_id, value={request_id}")
        r.hset(k, "pending_request_id", request_id)
        
        logger.debug(f"Setting Redis key TTL: key={k}, ttl={USER_STATE_TTL}")
        r.expire(k, USER_STATE_TTL)
        
        logger.info(f"Successfully set pending prompt state: user_id={user_id}, request_id={request_id}")
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error when setting pending state for user_id={user_id}: {e}")
    except redis.exceptions.TimeoutError as e:
        logger.error(f"Redis timeout when setting pending state for user_id={user_id}: {e}")
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error when setting pending state for user_id={user_id}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error setting pending state for user_id={user_id}, request_id={request_id}: {e}")

def get_pending_state(user_id: int) -> Optional[str]:
    """
    Retrieve pending request ID for a user
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Optional[str]: Pending request ID or None if not found
    """
    logger.debug(f"Getting pending state for user_id={user_id}")
    
    try:
        r = get_redis_connection(config.settings)
        k = _user_state_key(user_id)
        
        logger.debug(f"Fetching Redis hash field: key={k}, field=pending_request_id")
        request_id = r.hget(k, "pending_request_id")
        
        if request_id:
            result = request_id.decode()
            logger.debug(f"Found pending state: user_id={user_id}, request_id={result}")
            return result
            
        logger.debug(f"No pending state found for user_id={user_id}")
        return None
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error when getting pending state for user_id={user_id}: {e}")
        return None
    except redis.exceptions.TimeoutError as e:
        logger.error(f"Redis timeout when getting pending state for user_id={user_id}: {e}")
        return None
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error when getting pending state for user_id={user_id}: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error getting pending state for user_id={user_id}: {e}")
        return None

def clear_pending_state(user_id: int):
    """
    Clear pending prompt state for a user
    
    Args:
        user_id: Telegram user ID
    """
    logger.debug(f"Clearing pending state for user_id={user_id}")
    
    try:
        r = get_redis_connection(config.settings)
        k = _user_state_key(user_id)
        
        logger.debug(f"Deleting Redis key: key={k}")
        r.delete(k)
        
        logger.info(f"Successfully cleared pending state for user_id={user_id}")
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error when clearing pending state for user_id={user_id}: {e}")
    except redis.exceptions.TimeoutError as e:
        logger.error(f"Redis timeout when clearing pending state for user_id={user_id}: {e}")
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error when clearing pending state for user_id={user_id}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error clearing pending state for user_id={user_id}: {e}")

def set_status_message(user_id: int, chat_id: int, message_id: int):
    """
    Store status message ID for a user and chat
    
    Args:
        user_id: Telegram user ID
        chat_id: Chat where status message was sent
        message_id: ID of the status message
    """
    logger.debug(f"Setting status message: user_id={user_id}, chat_id={chat_id}, message_id={message_id}")
    
    try:
        r = get_redis_connection(config.settings)
        k = _user_state_key(user_id)
        field = f"status_message:{chat_id}"
        
        logger.debug(f"Setting Redis hash: key={k}, field={field}, value={message_id}")
        r.hset(k, field, message_id)
        
        logger.debug(f"Setting Redis key TTL: key={k}, ttl={USER_STATE_TTL}")
        r.expire(k, USER_STATE_TTL)
        
        logger.info(f"Successfully set status message: user_id={user_id}, chat_id={chat_id}, message_id={message_id}")
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error when setting status message for user_id={user_id}, chat_id={chat_id}: {e}")
    except redis.exceptions.TimeoutError as e:
        logger.error(f"Redis timeout when setting status message for user_id={user_id}, chat_id={chat_id}: {e}")
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error when setting status message for user_id={user_id}, chat_id={chat_id}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error setting status message for user_id={user_id}, chat_id={chat_id}: {e}")

def get_status_message(user_id: int, chat_id: int) -> Optional[int]:
    """
    Retrieve status message ID for a user and chat
    
    Args:
        user_id: Telegram user ID
        chat_id: Chat where status message was sent
        
    Returns:
        Optional[int]: Status message ID or None if not found
    """
    logger.debug(f"Getting status message: user_id={user_id}, chat_id={chat_id}")
    
    try:
        r = get_redis_connection(config.settings)
        k = _user_state_key(user_id)
        field = f"status_message:{chat_id}"
        
        logger.debug(f"Fetching Redis hash field: key={k}, field={field}")
        msg_id = r.hget(k, field)
        
        if msg_id:
            try:
                result = int(msg_id)
                logger.debug(f"Found status message: user_id={user_id}, chat_id={chat_id}, message_id={result}")
                return result
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid message ID format in Redis: {msg_id}, error: {e}")
                return None
                
        logger.debug(f"No status message found for user_id={user_id}, chat_id={chat_id}")
        return None
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error when getting status message for user_id={user_id}, chat_id={chat_id}: {e}")
        return None
    except redis.exceptions.TimeoutError as e:
        logger.error(f"Redis timeout when getting status message for user_id={user_id}, chat_id={chat_id}: {e}")
        return None
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error when getting status message for user_id={user_id}, chat_id={chat_id}: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error getting status message for user_id={user_id}, chat_id={chat_id}: {e}")
        return None

def store_request_data(request_id: str, data: Dict[str, Any]):
    """
    Store request data in Redis
    
    Args:
        request_id: Unique request identifier
        data: Dictionary of data to store
    """
    logger.debug(f"Storing request data: request_id={request_id}, data_keys={list(data.keys())}")
    
    try:
        r = get_redis_connection(config.settings)
        k = _request_data_key(request_id)
        
        # Convert all values to strings for Redis
        string_data = {k: str(v) for k, v in data.items()}
        
        # Don't log potentially sensitive data but log the operation
        logger.debug(f"Setting Redis hash: key={k}, fields={len(string_data)} key-value pairs")
        r.hset(k, mapping=string_data)
        
        logger.debug(f"Setting Redis key TTL: key={k}, ttl={REQUEST_DATA_TTL}")
        r.expire(k, REQUEST_DATA_TTL)
        
        logger.info(f"Successfully stored request data: request_id={request_id}, fields={list(data.keys())}")
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error when storing request data for request_id={request_id}: {e}")
    except redis.exceptions.TimeoutError as e:
        logger.error(f"Redis timeout when storing request data for request_id={request_id}: {e}")
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error when storing request data for request_id={request_id}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error storing request data for request_id={request_id}: {e}")

def update_request_status(request_id: str, status: str):
    """
    Update the status field of request data
    
    Args:
        request_id: Unique request identifier
        status: New status value
    """
    logger.debug(f"Updating request status: request_id={request_id}, status={status}")
    
    try:
        r = get_redis_connection(config.settings)
        k = _request_data_key(request_id)
        
        logger.debug(f"Setting Redis hash field: key={k}, field=status, value={status}")
        r.hset(k, "status", status)
        
        logger.debug(f"Setting Redis key TTL: key={k}, ttl={REQUEST_DATA_TTL}")
        r.expire(k, REQUEST_DATA_TTL)
        
        logger.info(f"Successfully updated request status: request_id={request_id}, status={status}")
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error when updating request status for request_id={request_id}: {e}")
    except redis.exceptions.TimeoutError as e:
        logger.error(f"Redis timeout when updating request status for request_id={request_id}: {e}")
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error when updating request status for request_id={request_id}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error updating request status for request_id={request_id}: {e}")

def get_request_data(request_id: str) -> Optional[Dict[str, str]]:
    """
    Retrieve request data from Redis
    
    Args:
        request_id: Unique request identifier
        
    Returns:
        Optional[Dict[str, str]]: Request data or None if not found
    """
    logger.debug(f"Getting request data: request_id={request_id}")
    
    try:
        r = get_redis_connection(config.settings)
        k = _request_data_key(request_id)
        
        logger.debug(f"Fetching all Redis hash fields: key={k}")
        d = r.hgetall(k)
        
        if d:
            try:
                result = {k.decode(): v.decode() for k, v in d.items()}
                logger.debug(f"Found request data: request_id={request_id}, fields={list(result.keys())}")
                return result
            except Exception as decode_error:
                logger.error(f"Error decoding Redis data for request_id={request_id}: {decode_error}")
                return None
                
        logger.debug(f"No request data found for request_id={request_id}")
        return None
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error when getting request data for request_id={request_id}: {e}")
        return None
    except redis.exceptions.TimeoutError as e:
        logger.error(f"Redis timeout when getting request data for request_id={request_id}: {e}")
        return None
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error when getting request data for request_id={request_id}: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error getting request data for request_id={request_id}: {e}")
        return None

def add_rq_job_id(request_id: str, rq_job_id: str):
    """
    Associate an RQ job ID with a request
    
    Args:
        request_id: Unique request identifier
        rq_job_id: RQ job ID
    """
    logger.debug(f"Adding RQ job ID: request_id={request_id}, rq_job_id={rq_job_id}")
    
    try:
        r = get_redis_connection(config.settings)
        k = _request_data_key(request_id)
        
        logger.debug(f"Setting Redis hash field: key={k}, field=rq_job_id, value={rq_job_id}")
        r.hset(k, "rq_job_id", rq_job_id)
        
        logger.debug(f"Setting Redis key TTL: key={k}, ttl={REQUEST_DATA_TTL}")
        r.expire(k, REQUEST_DATA_TTL)
        
        logger.info(f"Successfully added RQ job ID: request_id={request_id}, rq_job_id={rq_job_id}")
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error when adding RQ job ID for request_id={request_id}: {e}")
    except redis.exceptions.TimeoutError as e:
        logger.error(f"Redis timeout when adding RQ job ID for request_id={request_id}: {e}")
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error when adding RQ job ID for request_id={request_id}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error adding RQ job ID for request_id={request_id}: {e}")