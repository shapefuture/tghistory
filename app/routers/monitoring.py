from fastapi import APIRouter, HTTPException, Depends, Request, Header
from typing import Optional, List, Dict, Any
import time
import logging
from app.shared.metrics import MetricsRetriever
from app.shared.redis_client import get_redis_connection
from app import config
import os
import psutil

router = APIRouter(tags=["monitoring"])

logger = logging.getLogger("api.monitoring")

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "sample_admin_token")

def get_current_admin(x_admin_token: Optional[str] = Header(None)) -> str:
    """
    Real admin authentication using X-Admin-Token header.
    """
    logger.debug(f"Admin authentication attempted: X-Admin-Token header received={bool(x_admin_token)}")
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        logger.warning("Admin authentication failed: missing or invalid token.")
        raise HTTPException(status_code=401, detail="Admin authentication failed.")
    logger.info("Admin authentication succeeded.")
    return "admin"

def check_redis_health() -> Dict[str, Any]:
    """
    Real Redis health check.
    """
    try:
        redis_conn = get_redis_connection(config.settings)
        pong = redis_conn.ping()
        if pong:
            logger.info("Redis health check succeeded.")
            return {"status": "ok", "detail": "Redis is healthy"}
        else:
            logger.error("Redis health check failed: PING returned False.")
            return {"status": "error", "detail": "Redis PING failed"}
    except Exception as e:
        logger.error(f"Redis health check error: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}

def check_system_health() -> Dict[str, Any]:
    """
    Real system health check using psutil.
    """
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.dirname(config.settings.OUTPUT_DIR_PATH))
        healthy = (
            cpu < 90 and
            mem.percent < 90 and
            disk.percent < 98
        )
        logger.info(f"System health check: cpu={cpu} mem={mem.percent} disk={disk.percent}")
        return {
            "status": "ok" if healthy else "warning",
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "disk_percent": disk.percent
        }
    except Exception as e:
        logger.error(f"System health check error: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}

async def get_overall_health() -> Dict[str, Any]:
    """
    Real overall health check.
    """
    redis_status = check_redis_health()
    system_status = check_system_health()
    status = (
        "error" if redis_status["status"] == "error" or system_status["status"] == "error"
        else "warning" if redis_status["status"] == "warning" or system_status["status"] == "warning"
        else "ok"
    )
    health = {
        "status": status,
        "redis": redis_status,
        "system": system_status,
        "timestamp": time.time()
    }
    logger.info(f"Overall health: {health}")
    return health

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

@router.get("/health/components", dependencies=[Depends(get_current_admin)])
async def component_health():
    logger.info("Component health endpoint called")
    try:
        result = await get_overall_health()
        logger.info(f"Component health result: {result}")
        return result
    except Exception as e:
        logger.error(f"Component health endpoint error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

@router.get("/metrics/system", dependencies=[Depends(get_current_admin)])
async def system_metrics(days: int = 1, interval_minutes: int = 5):
    logger.info(f"System metrics endpoint called: days={days}, interval_minutes={interval_minutes}")
    try:
        metrics = MetricsRetriever.get_system_metrics(days, interval_minutes)
        logger.info("System metrics endpoint success")
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"System metrics endpoint error: {e}", exc_info=True)
        return {"metrics": {}, "error": str(e)}

@router.get("/metrics/api", dependencies=[Depends(get_current_admin)])
async def api_metrics(days: int = 1, endpoints: Optional[List[str]] = None):
    logger.info(f"API metrics endpoint called: days={days}, endpoints={endpoints}")
    try:
        metrics = MetricsRetriever.get_api_metrics(days, endpoints)
        logger.info("API metrics endpoint success")
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"API metrics endpoint error: {e}", exc_info=True)
        return {"metrics": {}, "error": str(e)}

@router.get("/metrics/users/{user_id}", dependencies=[Depends(get_current_admin)])
async def user_metrics(user_id: int, days: int = 7):
    logger.info(f"User metrics endpoint called: user_id={user_id}, days={days}")
    try:
        metrics = MetricsRetriever.get_user_metrics(user_id, days)
        if not metrics:
            logger.warning(f"User metrics not found: user_id={user_id}, days={days}")
            raise HTTPException(status_code=404, detail="User metrics not found")
        logger.info(f"User metrics retrieved: user_id={user_id}")
        return metrics
    except HTTPException as he:
        logger.error(f"User metrics HTTPException: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"User metrics endpoint error: {e}", exc_info=True)
        return {"metrics": {}, "error": str(e)}

@router.get("/metrics/jobs/{job_id}", dependencies=[Depends(get_current_admin)])
async def job_metrics(job_id: str):
    logger.info(f"Job metrics endpoint called: job_id={job_id}")
    try:
        metrics = MetricsRetriever.get_job_metrics(job_id)
        if not metrics:
            logger.warning(f"Job metrics not found: job_id={job_id}")
            raise HTTPException(status_code=404, detail="Job metrics not found")
        logger.info(f"Job metrics retrieved: job_id={job_id}")
        return metrics
    except HTTPException as he:
        logger.error(f"Job metrics HTTPException: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Job metrics endpoint error: {e}", exc_info=True)
        return {"metrics": {}, "error": str(e)}
