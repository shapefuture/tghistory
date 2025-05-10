import redis
from rq import Queue
from app import config  # Fixed: Using absolute import instead
import logging
import traceback

logger = logging.getLogger("shared.redis_client")

_redis_instance = None

def get_redis_connection(settings: config.Settings):
    global _redis_instance
    logger.debug(f"Getting Redis connection for URL: {settings.REDIS_URL}")
    if _redis_instance is not None:
        return _redis_instance
    try:
        _redis_instance = redis.Redis.from_url(settings.REDIS_URL)
        _redis_instance.ping()
        logger.info("Redis connection established successfully")
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        raise
    except redis.exceptions.TimeoutError as e:
        logger.error(f"Redis timeout: {e}")
        raise
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unknown error connecting to Redis: {e}\n{traceback.format_exc()}")
        raise
    return _redis_instance

def get_rq_queue(redis_conn, settings: config.Settings):
    logger.debug(f"Getting RQ queue: {settings.RQ_QUEUE_NAME}")
    try:
        queue = Queue(settings.RQ_QUEUE_NAME, connection=redis_conn)
        logger.info(f"RQ queue '{settings.RQ_QUEUE_NAME}' obtained successfully")
        return queue
    except Exception as e:
        logger.error(f"Failed to get RQ queue: {e}\n{traceback.format_exc()}")
        raise
