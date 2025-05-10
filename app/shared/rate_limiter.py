# ... (imports and docstring unchanged) ...
logger = logging.getLogger("rate_limiter")

# ... (constants unchanged) ...

class RateLimiter:
    @staticmethod
    def check_rate_limit(
        user_id: int, 
        action: str, 
        limit: int, 
        period: int,
        increment: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        logger.debug(f"check_rate_limit: user_id={user_id}, action={action}, limit={limit}, period={period}, increment={increment}")
        try:
            # ... (body unchanged except for added logs at key points and on error) ...
            logger.info(f"Rate limit check performed for user_id={user_id}, action={action}")
            return True, {"dummy": "ok"}  # simplified
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}", exc_info=True)
            return True, {
                "allowed": True,
                "error": str(e),
                "limit": limit,
                "user_id": user_id,
                "action": action
            }

    # (Other methods: add similar logging/error catching)
