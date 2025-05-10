"""
Health check module for monitoring system components.
Provides functions to check the health of Redis, Telegram connection,
and overall system status.
"""
import logging
import time
import socket
import os
import psutil
from telethon.sync import TelegramClient
from telethon.errors import AuthKeyError, ServerError
from redis.exceptions import RedisError
from typing import Dict, List, Tuple, Any, Optional

from app import config
from app.shared.redis_client import get_redis_connection
from app.userbot.client import get_telethon_client

logger = logging.getLogger("health")

class HealthStatus:
    """Health status constants"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"

def check_redis_health() -> Dict[str, Any]:
    """
    Check Redis connection health
    
    Returns:
        Dict containing status and metadata about Redis health
    """
    start_time = time.time()
    status = HealthStatus.OK
    details = {}
    
    try:
        redis_conn = get_redis_connection(config.settings)
        
        # Basic ping to verify connection
        ping_result = redis_conn.ping()
        if not ping_result:
            status = HealthStatus.ERROR
            details["error"] = "Redis ping failed"
        
        # Get server info for more detailed health metrics
        info = redis_conn.info()
        
        details.update({
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            "version": info.get("redis_version", "unknown")
        })
        
        # Check for warning signs
        if info.get("used_memory_peak_perc", 0) > 90:
            status = HealthStatus.WARNING
            details["warning"] = "Memory usage high"
            
    except RedisError as e:
        status = HealthStatus.ERROR
        details["error"] = f"Redis connection error: {str(e)}"
    except Exception as e:
        status = HealthStatus.ERROR
        details["error"] = f"Unexpected error: {str(e)}"
    
    execution_time = time.time() - start_time
    
    return {
        "component": "redis",
        "status": status,
        "details": details,
        "execution_time_ms": round(execution_time * 1000, 2)
    }

async def check_telegram_health(test_connection: bool = True) -> Dict[str, Any]:
    """
    Check Telegram API connection health
    
    Args:
        test_connection: Whether to attempt an actual connection
    
    Returns:
        Dict containing status and metadata about Telegram connection health
    """
    start_time = time.time()
    status = HealthStatus.OK
    details = {}
    
    try:
        # Check if credentials are configured
        if not config.settings.TELEGRAM_API_ID or not config.settings.TELEGRAM_API_HASH:
            status = HealthStatus.ERROR
            details["error"] = "Telegram API credentials not configured"
            return {
                "component": "telegram",
                "status": status,
                "details": details,
                "execution_time_ms": round((time.time() - start_time) * 1000, 2)
            }
            
        # Check if session file exists
        if not os.path.exists(config.settings.TELEGRAM_SESSION_PATH):
            status = HealthStatus.WARNING
            details["warning"] = "Session file does not exist"
        
        if test_connection:
            # Attempt an actual connection (lightweight)
            client = get_telethon_client(config.settings)
            
            try:
                await client.connect()
                me = await client.get_me() if await client.is_user_authorized() else None
                
                if me:
                    details["user_id"] = me.id
                    details["username"] = me.username
                    details["authorized"] = True
                else:
                    status = HealthStatus.WARNING
                    details["warning"] = "Connected but not authorized"
                    details["authorized"] = False
                    
            except AuthKeyError:
                status = HealthStatus.ERROR
                details["error"] = "Invalid authorization key"
            except ServerError:
                status = HealthStatus.ERROR
                details["error"] = "Telegram server error"
            except Exception as e:
                status = HealthStatus.ERROR
                details["error"] = f"Connection error: {str(e)}"
            finally:
                if client.is_connected():
                    await client.disconnect()
    
    except Exception as e:
        status = HealthStatus.ERROR
        details["error"] = f"Unexpected error: {str(e)}"
    
    execution_time = time.time() - start_time
    
    return {
        "component": "telegram",
        "status": status,
        "details": details,
        "execution_time_ms": round(execution_time * 1000, 2)
    }

def check_system_health() -> Dict[str, Any]:
    """
    Check system health (CPU, memory, disk)
    
    Returns:
        Dict containing status and metadata about system health
    """
    start_time = time.time()
    status = HealthStatus.OK
    details = {}
    
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        details["cpu_percent"] = cpu_percent
        
        # Memory usage
        memory = psutil.virtual_memory()
        details["memory_percent"] = memory.percent
        details["memory_used_gb"] = round(memory.used / (1024**3), 2)
        details["memory_total_gb"] = round(memory.total / (1024**3), 2)
        
        # Disk usage
        disk_path = os.path.dirname(config.settings.OUTPUT_DIR_PATH)
        disk = psutil.disk_usage(disk_path)
        details["disk_percent"] = disk.percent
        details["disk_used_gb"] = round(disk.used / (1024**3), 2)
        details["disk_total_gb"] = round(disk.total / (1024**3), 2)
        details["disk_path"] = disk_path
        
        # Set status based on thresholds
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            status = HealthStatus.ERROR
            details["error"] = "Critical resource usage"
        elif cpu_percent > 75 or memory.percent > 75 or disk.percent > 75:
            status = HealthStatus.WARNING
            details["warning"] = "High resource usage"
            
    except Exception as e:
        status = HealthStatus.ERROR
        details["error"] = f"Unexpected error: {str(e)}"
    
    execution_time = time.time() - start_time
    
    return {
        "component": "system",
        "status": status,
        "details": details,
        "execution_time_ms": round(execution_time * 1000, 2)
    }

def check_network_health() -> Dict[str, Any]:
    """
    Check network connectivity
    
    Returns:
        Dict containing status and metadata about network health
    """
    start_time = time.time()
    status = HealthStatus.OK
    details = {}
    
    # Define external services to check
    services = [
        ("api.telegram.org", 443),  # Telegram API
        ("www.google.com", 443),    # General internet connectivity
    ]
    
    results = []
    for host, port in services:
        try:
            # Attempt to create a socket connection with timeout
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            conn_start = time.time()
            s.connect((host, port))
            conn_time = time.time() - conn_start
            s.close()
            
            results.append({
                "host": host,
                "port": port,
                "status": "connected",
                "response_time_ms": round(conn_time * 1000, 2)
            })
        except Exception as e:
            results.append({
                "host": host,
                "port": port,
                "status": "failed",
                "error": str(e)
            })
            status = HealthStatus.ERROR
    
    details["connectivity_tests"] = results
    
    # If any connection failed, mark as error
    if status == HealthStatus.ERROR:
        details["error"] = "One or more connectivity tests failed"
    
    execution_time = time.time() - start_time
    
    return {
        "component": "network",
        "status": status,
        "details": details,
        "execution_time_ms": round(execution_time * 1000, 2)
    }

async def get_overall_health(include_telegram: bool = True) -> Dict[str, Any]:
    """
    Get overall health status of all system components
    
    Args:
        include_telegram: Whether to include Telegram health check
        
    Returns:
        Dict containing overall status and individual component statuses
    """
    start_time = time.time()
    
    # Run all health checks
    checks = []
    
    # Always run these checks
    checks.append(check_redis_health())
    checks.append(check_system_health())
    checks.append(check_network_health())
    
    # Optionally run Telegram check (requires async)
    if include_telegram:
        checks.append(await check_telegram_health())
    
    # Determine overall status
    if any(check["status"] == HealthStatus.ERROR for check in checks):
        overall_status = HealthStatus.ERROR
    elif any(check["status"] == HealthStatus.WARNING for check in checks):
        overall_status = HealthStatus.WARNING
    else:
        overall_status = HealthStatus.OK
    
    execution_time = time.time() - start_time
    
    return {
        "timestamp": time.time(),
        "status": overall_status,
        "components": checks,
        "execution_time_ms": round(execution_time * 1000, 2)
    }