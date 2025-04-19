"""
Rate limiter module for controlling request rates.

Provides functionality to limit the rate of requests from users
and prevent abuse of the system.
"""
import time
import logging
from typing import Tuple, Optional, Dict, List, Any
import json

from app import config
from app.shared.redis_client import get_redis_connection

logger = logging.getLogger("rate_limiter")

# Redis key prefixes for rate limiting
USER_RATE_LIMIT_KEY = "rate:user:{user_id}:{action}"
GLOBAL_RATE_LIMIT_KEY = "rate:global:{action}"

class RateLimiter:
    """Rate limiter for controlling request frequency"""
    
    @staticmethod
    def check_rate_limit(
        user_id: int, 
        action: str, 
        limit: int, 
        period: int,
        increment: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a user has exceeded rate limits for an action
        
        Args:
            user_id: The user ID
            action: The action being performed (e.g., "extract", "summarize")
            limit: Maximum number of requests allowed in the period
            period: Time period in seconds
            increment: Whether to increment the counter if not limited
            
        Returns:
            Tuple of (is_allowed, rate_info)
        """
        try:
            redis_conn = get_redis_connection(config.settings)
            key = USER_RATE_LIMIT_KEY.format(user_id=user_id, action=action)
            
            # Get current timestamp
            now = time.time()
            min_timestamp = now - period
            
            # Get all requests in the time window
            redis_conn.zremrangebyscore(key, 0, min_timestamp)
            
            # Count remaining requests
            current_count = redis_conn.zcard(key)
            
            # If under limit, allow and increment if needed
            if current_count < limit:
                if increment:
                    redis_conn.zadd(key, {str(now): now})
                    # Set expiration to ensure cleanup
                    redis_conn.expire(key, period * 2)
                
                return True, {
                    "allowed": True,
                    "current_count": current_count + (1 if increment else 0),
                    "limit": limit,
                    "remaining": limit - current_count - (1 if increment else 0),
                    "reset_after": period,
                    "user_id": user_id,
                    "action": action
                }
            else:
                # Get oldest timestamp to calculate reset time
                oldest = float(redis_conn.zrange(key, 0, 0, withscores=True)[0][1])
                reset_after = int(oldest + period - now) + 1  # Add 1 second buffer
                
                return False, {
                    "allowed": False,
                    "current_count": current_count,
                    "limit": limit,
                    "remaining": 0,
                    "reset_after": reset_after,
                    "user_id": user_id,
                    "action": action
                }
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Default to allowing in case of error
            return True, {
                "allowed": True,
                "error": str(e),
                "limit": limit,
                "user_id": user_id,
                "action": action
            }
    
    @staticmethod
    def check_global_rate_limit(
        action: str, 
        limit: int, 
        period: int,
        increment: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if global rate limit has been exceeded for an action
        
        Args:
            action: The action being performed (e.g., "extract", "summarize")
            limit: Maximum number of requests allowed in the period
            period: Time period in seconds
            increment: Whether to increment the counter if not limited
            
        Returns:
            Tuple of (is_allowed, rate_info)
        """
        try:
            redis_conn = get_redis_connection(config.settings)
            key = GLOBAL_RATE_LIMIT_KEY.format(action=action)
            
            # Get current timestamp
            now = time.time()
            min_timestamp = now - period
            
            # Get all requests in the time window
            redis_conn.zremrangebyscore(key, 0, min_timestamp)
            
            # Count remaining requests
            current_count = redis_conn.zcard(key)
            
            # If under limit, allow and increment if needed
            if current_count < limit:
                if increment:
                    redis_conn.zadd(key, {str(now): now})
                    # Set expiration to ensure cleanup
                    redis_conn.expire(key, period * 2)
                
                return True, {
                    "allowed": True,
                    "current_count": current_count + (1 if increment else 0),
                    "limit": limit,
                    "remaining": limit - current_count - (1 if increment else 0),
                    "reset_after": period,
                    "action": action
                }
            else:
                # Get oldest timestamp to calculate reset time
                oldest = float(redis_conn.zrange(key, 0, 0, withscores=True)[0][1])
                reset_after = int(oldest + period - now) + 1  # Add 1 second buffer
                
                return False, {
                    "allowed": False,
                    "current_count": current_count,
                    "limit": limit,
                    "remaining": 0,
                    "reset_after": reset_after,
                    "action": action
                }
        except Exception as e:
            logger.error(f"Global rate limit check failed: {e}")
            # Default to allowing in case of error
            return True, {
                "allowed": True,
                "error": str(e),
                "limit": limit,
                "action": action
            }
    
    @staticmethod
    def get_rate_limits(user_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get current rate limit status for a user
        
        Args:
            user_id: The user ID
            
        Returns:
            Dict mapping actions to rate limit info
        """
        try:
            redis_conn = get_redis_connection(config.settings)
            
            # Find all rate limit keys for this user
            keys = []
            for key in redis_conn.scan_iter(match=f"rate:user:{user_id}:*"):
                keys.append(key.decode())
            
            result = {}
            now = time.time()
            
            for key in keys:
                # Extract action from key
                action = key.split(":")[-1]
                
                # Get all requests in the time window
                requests = redis_conn.zrange(key, 0, -1, withscores=True)
                
                if not requests:
                    continue
                
                # Find oldest request to determine reset time
                oldest_time = min(score for _, score in requests)
                newest_time = max(score for _, score in requests)
                
                # Determine period based on key TTL
                ttl = redis_conn.ttl(key)
                period = ttl // 2 if ttl > 0 else 3600  # Default to 1 hour
                
                # Count requests
                count = len(requests)
                
                result[action] = {
                    "count": count,
                    "oldest_request": int(oldest_time),
                    "newest_request": int(newest_time),
                    "age_seconds": int(now - oldest_time),
                    "period_seconds": period,
                    "estimated_resets_after": int(oldest_time + period - now)
                }
            
            return result
        except Exception as e:
            logger.error(f"Failed to get rate limits: {e}")
            return {}