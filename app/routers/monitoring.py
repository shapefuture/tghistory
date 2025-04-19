"""
FastAPI router for health checks and metrics.

Provides endpoints for checking system health and retrieving metrics
about system usage and performance.
"""
import logging
import time
import json
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app import config
from app.shared.health import get_overall_health, check_redis_health, check_system_health, check_network_health
from app.shared.metrics import MetricsRetriever

router = APIRouter(tags=["monitoring"])

logger = logging.getLogger("api.monitoring")

# Security warning for developers
"""
SECURITY WARNING: Health check and metrics endpoints should be properly secured
in a production environment with authentication and authorization controls.
"""

async def get_current_admin(request: Request):
    """
    PLACEHOLDER ADMIN AUTH - REPLACE BEFORE PRODUCTION
    
    This is NOT a secure authentication system for admin access.
    """
    # In production, implement proper admin authentication here
    
    # For now, return a placeholder admin ID
    return "admin"

@router.get("/health")
async def health_check(full: bool = False):
    """
    Basic health check endpoint that returns system health status
    
    Args:
        full: Whether to include detailed component statuses
    """
    if full:
        # Full health check with all components
        return await get_overall_health()
    else:
        # Basic health check (redis + system only, no telegram)
        redis_health = check_redis_health()
        system_health = check_system_health()
        
        # Determine overall status
        if redis_health["status"] == "error" or system_health["status"] == "error":
            status = "error"
        elif redis_health["status"] == "warning" or system_health["status"] == "warning":
            status = "warning"
        else:
            status = "ok"
        
        return {
            "status": status,
            "timestamp": time.time()
        }

@router.get("/health/components", dependencies=[Depends(get_current_admin)])
async def component_health():
    """
    Detailed health check showing status of all system components
    """
    return await get_overall_health()

@router.get("/metrics/system", dependencies=[Depends(get_current_admin)])
async def system_metrics(days: int = 1, interval_minutes: int = 5):
    """
    Get system metrics for the specified time period
    
    Args:
        days: Number of days to retrieve data for
        interval_minutes: Interval between data points
    """
    metrics = MetricsRetriever.get_system_metrics(days, interval_minutes)
    return {"metrics": metrics}

@router.get("/metrics/api", dependencies=[Depends(get_current_admin)])
async def api_metrics(days: int = 1, endpoints: Optional[List[str]] = None):
    """
    Get API metrics for the specified endpoints
    
    Args:
        days: Number of days to retrieve data for
        endpoints: Optional list of endpoints to filter by
    """
    metrics = MetricsRetriever.get_api_metrics(days, endpoints)
    return {"metrics": metrics}

@router.get("/metrics/users/{user_id}", dependencies=[Depends(get_current_admin)])
async def user_metrics(user_id: int, days: int = 7):
    """
    Get metrics for a specific user
    
    Args:
        user_id: The user ID
        days: Number of days to retrieve data for
    """
    metrics = MetricsRetriever.get_user_metrics(user_id, days)
    if not metrics:
        raise HTTPException(status_code=404, detail="User metrics not found")
    return metrics

@router.get("/metrics/jobs/{job_id}", dependencies=[Depends(get_current_admin)])
async def job_metrics(job_id: str):
    """
    Get metrics for a specific job
    
    Args:
        job_id: The job ID
    """
    metrics = MetricsRetriever.get_job_metrics(job_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Job metrics not found")
    return metrics