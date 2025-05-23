import time
import logging
from typing import Tuple, Dict, Any

from app.shared.redis_client import get_redis_connection
from app import config

logger = logging.getLogger("rate_limiter")

USER_RATE_LIMIT_KEY = "rate:user:{user_id}:{action}"
GLOBAL_RATE_LIMIT_KEY = "rate:global:{action}"

class RateLimiter:
    @staticmethod
    def check_rate_limit(
        user_id: int,
        action: str,
        limit: int,
        period: int,
        increment: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        logger.debug(f"[ENTRY] check_rate_limit(user_id={user_id}, action={action}, limit={limit}, period={period}, increment={increment})")
        try:
            redis_conn = get_redis_connection(config.settings)
            key = USER_RATE_LIMIT_KEY.format(user_id=user_id, action=action)
            now = time.time()
            min_timestamp = now - period
            redis_conn.zremrangebyscore(key, 0, min_timestamp)
            current_count = redis_conn.zcard(key)
            logger.debug(f"Current count for {key}: {current_count}")
            if current_count < limit:
                if increment:
                    redis_conn.zadd(key, {str(now): now})
                    redis_conn.expire(key, period * 2)
                logger.info(f"User {user_id} action '{action}' allowed (count={current_count+1}/{limit})")
                result = {
                    "allowed": True,
                    "current_count": current_count + (1 if increment else 0),
                    "limit": limit,
                    "remaining": limit - current_count - (1 if increment else 0),
                    "reset_after": period,
                    "user_id": user_id,
                    "action": action
                }
                logger.debug(f"[EXIT] check_rate_limit result: {result}")
                return True, result
            else:
                oldest = float(redis_conn.zrange(key, 0, 0, withscores=True)[0][1])
                reset_after = int(oldest + period - now) + 1
                logger.info(f"User {user_id} action '{action}' rate limited (count={current_count}/{limit})")
                result = {
                    "allowed": False,
                    "current_count": current_count,
                    "limit": limit,
                    "remaining": 0,
                    "reset_after": reset_after,
                    "user_id": user_id,
                    "action": action
                }
                logger.debug(f"[EXIT] check_rate_limit result: {result}")
                return False, result
        except Exception as e:
            logger.error(f"[ERROR] Rate limit check failed: {e}", exc_info=True)
            result = {
                "allowed": True,
                "error": str(e),
                "limit": limit,
                "user_id": user_id,
                "action": action
            }
            logger.debug(f"[EXIT] check_rate_limit error result: {result}")
            return True, result

    @staticmethod
    def check_global_rate_limit(
        action: str,
        limit: int,
        period: int,
        increment: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        logger.debug(f"[ENTRY] check_global_rate_limit(action={action}, limit={limit}, period={period}, increment={increment})")
        try:
            redis_conn = get_redis_connection(config.settings)
            key = GLOBAL_RATE_LIMIT_KEY.format(action=action)
            now = time.time()
            min_timestamp = now - period
            redis_conn.zremrangebyscore(key, 0, min_timestamp)
            current_count = redis_conn.zcard(key)
            logger.debug(f"Current global count for {key}: {current_count}")
            if current_count < limit:
                if increment:
                    redis_conn.zadd(key, {str(now): now})
                    redis_conn.expire(key, period * 2)
                logger.info(f"Global action '{action}' allowed (count={current_count+1}/{limit})")
                result = {
                    "allowed": True,
                    "current_count": current_count + (1 if increment else 0),
                    "limit": limit,
                    "remaining": limit - current_count - (1 if increment else 0),
                    "reset_after": period,
                    "action": action
                }
                logger.debug(f"[EXIT] check_global_rate_limit result: {result}")
                return True, result
            else:
                oldest = float(redis_conn.zrange(key, 0, 0, withscores=True)[0][1])
                reset_after = int(oldest + period - now) + 1
                logger.info(f"Global action '{action}' rate limited (count={current_count}/{limit})")
                result = {
                    "allowed": False,
                    "current_count": current_count,
                    "limit": limit,
                    "remaining": 0,
                    "reset_after": reset_after,
                    "action": action
                }
                logger.debug(f"[EXIT] check_global_rate_limit result: {result}")
                return False, result
        except Exception as e:
            logger.error(f"[ERROR] Global rate limit check failed: {e}", exc_info=True)
            result = {
                "allowed": True,
                "error": str(e),
                "limit": limit,
                "action": action
            }
            logger.debug(f"[EXIT] check_global_rate_limit error result: {result}")
            return True, result

    @staticmethod
    def get_rate_limits(user_id: int) -> Dict[str, Dict[str, Any]]:
        logger.debug(f"[ENTRY] get_rate_limits(user_id={user_id})")
        try:
            redis_conn = get_redis_connection(config.settings)
            keys = []
            for key in redis_conn.scan_iter(match=f"rate:user:{user_id}:*"):
                keys.append(key.decode())
            logger.debug(f"Rate limit keys found: {keys}")
            result = {}
            now = time.time()
            for key in keys:
                action = key.split(":")[-1]
                requests = redis_conn.zrange(key, 0, -1, withscores=True)
                if not requests:
                    continue
                oldest_time = min(score for _, score in requests)
                newest_time = max(score for _, score in requests)
                ttl = redis_conn.ttl(key)
                period = ttl // 2 if ttl > 0 else 3600
                count = len(requests)
                result[action] = {
                    "count": count,
                    "oldest_request": int(oldest_time),
                    "newest_request": int(newest_time),
                    "age_seconds": int(now - oldest_time),
                    "period_seconds": period,
                    "estimated_resets_after": int(oldest_time + period - now)
                }
            logger.info(f"Rate limits retrieved for user_id={user_id}: actions={list(result.keys())}")
            logger.debug(f"[EXIT] get_rate_limits result: {result}")
            return result
        except Exception as e:
            logger.error(f"[ERROR] Failed to get rate limits: {e}", exc_info=True)
            return {}
