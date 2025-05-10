# ... (imports and docstring unchanged) ...
router = APIRouter(tags=["monitoring"])

logger = logging.getLogger("api.monitoring")

# ... (auth function unchanged) ...

@router.get("/health")
async def health_check(full: bool = False):
    logger.info(f"Health check endpoint called, full={full}")
    try:
        if full:
            result = await get_overall_health()
        else:
            redis_health = check_redis_health()
            system_health = check_system_health()
            status = (
                "error" if redis_health["status"] == "error" or system_health["status"] == "error"
                else "warning" if redis_health["status"] == "warning" or system_health["status"] == "warning"
                else "ok"
            )
            result = {"status": status, "timestamp": time.time()}
        logger.info(f"Health check result: {result}")
        return result
    except Exception as e:
        logger.error(f"Health check endpoint error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

# (All other endpoints: add similar try/except and log all requests and errors)
