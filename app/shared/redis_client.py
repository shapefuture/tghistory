import redis
from rq import Queue
from . import config

_redis_instance = None

def get_redis_connection(settings: config.Settings):
    global _redis_instance
    if _redis_instance is not None:
        return _redis_instance
    try:
        _redis_instance = redis.Redis.from_url(settings.REDIS_URL)
        _redis_instance.ping()
    except redis.exceptions.RedisError as e:
        raise RuntimeError(f"Failed to connect to Redis: {e}")
    return _redis_instance

def get_rq_queue(redis_conn, settings: config.Settings):
    return Queue(settings.RQ_QUEUE_NAME, connection=redis_conn)