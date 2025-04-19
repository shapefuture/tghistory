"""
Metrics collection module for tracking system usage and performance.

This module provides functionality to collect, store, and retrieve metrics
about system usage, job performance, and resource utilization.
"""
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import os
import multiprocessing

from app import config
from app.shared.redis_client import get_redis_connection

logger = logging.getLogger("metrics")

# Redis key prefixes for metrics
JOB_METRICS_KEY = "metrics:job:{job_id}"
USER_METRICS_KEY = "metrics:user:{user_id}"
SYSTEM_METRICS_KEY = "metrics:system:{date}"
API_METRICS_KEY = "metrics:api:{endpoint}:{date}"

# TTL for metrics in Redis (in seconds)
USER_METRICS_TTL = 60 * 60 * 24 * 30  # 30 days
JOB_METRICS_TTL = 60 * 60 * 24 * 7    # 7 days
SYSTEM_METRICS_TTL = 60 * 60 * 24 * 7 # 7 days
API_METRICS_TTL = 60 * 60 * 24 * 7    # 7 days

class MetricsCollector:
    """Collects and stores metrics about system usage and performance"""
    
    @staticmethod
    def record_job_metrics(job_id: str, metrics: Dict[str, Any]) -> bool:
        """
        Record metrics for a specific job
        
        Args:
            job_id: The ID of the job
            metrics: Dict containing metrics to record
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            redis_conn = get_redis_connection(config.settings)
            key = JOB_METRICS_KEY.format(job_id=job_id)
            
            # Add timestamp if not provided
            if "timestamp" not in metrics:
                metrics["timestamp"] = time.time()
                
            # Store metrics as JSON
            redis_conn.hset(key, mapping={
                k: json.dumps(v) for k, v in metrics.items()
            })
            
            # Set TTL
            redis_conn.expire(key, JOB_METRICS_TTL)
            
            return True
        except Exception as e:
            logger.error(f"Failed to record job metrics: {e}")
            return False
    
    @staticmethod
    def record_user_metrics(user_id: int, action: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Record user activity metrics
        
        Args:
            user_id: The user ID
            action: The action performed (e.g., "extract", "summarize")
            metadata: Additional metadata about the action
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            redis_conn = get_redis_connection(config.settings)
            key = USER_METRICS_KEY.format(user_id=user_id)
            
            # Get current date in YYYY-MM-DD format
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Create metrics data
            data = {
                "timestamp": time.time(),
                "action": action
            }
            
            if metadata:
                data.update(metadata)
            
            # Append to list of actions for today
            redis_conn.lpush(f"{key}:{today}", json.dumps(data))
            
            # Increment action counter
            redis_conn.hincrby(f"{key}:counts", action, 1)
            redis_conn.hincrby(f"{key}:counts", f"{action}:{today}", 1)
            
            # Set TTL
            redis_conn.expire(f"{key}:{today}", USER_METRICS_TTL)
            redis_conn.expire(f"{key}:counts", USER_METRICS_TTL)
            
            return True
        except Exception as e:
            logger.error(f"Failed to record user metrics: {e}")
            return False
    
    @staticmethod
    def record_system_metrics() -> bool:
        """
        Record system metrics (CPU, memory, disk usage)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import psutil
            
            redis_conn = get_redis_connection(config.settings)
            today = datetime.now().strftime("%Y-%m-%d")
            key = SYSTEM_METRICS_KEY.format(date=today)
            
            # Collect system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.dirname(config.settings.OUTPUT_DIR_PATH))
            
            # Count active workers
            worker_count = len([p for p in psutil.process_iter(['pid', 'name']) 
                               if 'python' in p.info['name'] and 'worker' in ' '.join(p.cmdline())])
            
            # Create metrics data
            data = {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_used_mb": disk.used / (1024 * 1024),
                "active_workers": worker_count,
                "load_avg": os.getloadavg()[0]  # 1-minute load average
            }
            
            # Store in Redis time series (list)
            redis_conn.lpush(key, json.dumps(data))
            
            # Trim list to keep only recent entries (e.g., 1440 = 1 per minute for 24 hours)
            redis_conn.ltrim(key, 0, 1439)
            
            # Set TTL
            redis_conn.expire(key, SYSTEM_METRICS_TTL)
            
            return True
        except Exception as e:
            logger.error(f"Failed to record system metrics: {e}")
            return False
    
    @staticmethod
    def record_api_metrics(endpoint: str, response_time: float, status_code: int) -> bool:
        """
        Record API endpoint metrics
        
        Args:
            endpoint: The API endpoint
            response_time: Response time in seconds
            status_code: HTTP status code
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            redis_conn = get_redis_connection(config.settings)
            today = datetime.now().strftime("%Y-%m-%d")
            key = API_METRICS_KEY.format(endpoint=endpoint, date=today)
            
            # Update counters
            redis_conn.hincrby(key, "total_calls", 1)
            redis_conn.hincrby(key, f"status_{status_code}", 1)
            
            # Update response time stats
            redis_conn.lpush(f"{key}:response_times", response_time)
            redis_conn.ltrim(f"{key}:response_times", 0, 999)  # Keep last 1000 response times
            
            current_count = int(redis_conn.hget(key, "total_calls") or 0)
            current_avg = float(redis_conn.hget(key, "avg_response_time") or 0)
            
            # Calculate new average
            if current_count == 1:  # First request
                new_avg = response_time
            else:
                new_avg = ((current_avg * (current_count - 1)) + response_time) / current_count
                
            redis_conn.hset(key, "avg_response_time", new_avg)
            
            # Set TTL
            redis_conn.expire(key, API_METRICS_TTL)
            redis_conn.expire(f"{key}:response_times", API_METRICS_TTL)
            
            return True
        except Exception as e:
            logger.error(f"Failed to record API metrics: {e}")
            return False

class MetricsRetriever:
    """Retrieves and formats metrics from storage"""
    
    @staticmethod
    def get_job_metrics(job_id: str) -> Dict[str, Any]:
        """
        Get metrics for a specific job
        
        Args:
            job_id: The ID of the job
            
        Returns:
            Dict containing job metrics or empty dict if not found
        """
        try:
            redis_conn = get_redis_connection(config.settings)
            key = JOB_METRICS_KEY.format(job_id=job_id)
            
            # Get all metrics for the job
            raw_metrics = redis_conn.hgetall(key)
            
            if not raw_metrics:
                return {}
                
            # Parse JSON values
            return {
                k.decode(): json.loads(v.decode()) 
                for k, v in raw_metrics.items()
            }
        except Exception as e:
            logger.error(f"Failed to get job metrics: {e}")
            return {}
    
    @staticmethod
    def get_user_metrics(user_id: int, days: int = 7, actions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get metrics for a specific user
        
        Args:
            user_id: The user ID
            days: Number of days to retrieve data for
            actions: Optional list of actions to filter by
            
        Returns:
            Dict containing user metrics or empty dict if not found
        """
        try:
            redis_conn = get_redis_connection(config.settings)
            key_prefix = USER_METRICS_KEY.format(user_id=user_id)
            
            # Get date range
            end_date = datetime.now()
            date_range = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") 
                         for i in range(days)]
            
            # Get action counts
            counts_key = f"{key_prefix}:counts"
            raw_counts = redis_conn.hgetall(counts_key)
            
            counts = {
                k.decode(): int(v.decode())
                for k, v in raw_counts.items()
                if actions is None or any(action in k.decode() for action in actions)
            }
            
            # Get daily activity
            daily_activity = {}
            for date in date_range:
                day_key = f"{key_prefix}:{date}"
                activity = redis_conn.lrange(day_key, 0, -1)
                
                if activity:
                    daily_activity[date] = [
                        json.loads(item.decode())
                        for item in activity
                        if actions is None or any(json.loads(item.decode()).get("action") == action for action in actions)
                    ]
            
            return {
                "counts": counts,
                "daily_activity": daily_activity
            }
        except Exception as e:
            logger.error(f"Failed to get user metrics: {e}")
            return {}
    
    @staticmethod
    def get_system_metrics(days: int = 1, interval_minutes: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get system metrics for the specified time period
        
        Args:
            days: Number of days to retrieve data for
            interval_minutes: Interval between data points (to reduce data volume)
            
        Returns:
            Dict containing system metrics grouped by date
        """
        try:
            redis_conn = get_redis_connection(config.settings)
            
            # Get date range
            end_date = datetime.now()
            date_range = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") 
                         for i in range(days)]
            
            result = {}
            for date in date_range:
                key = SYSTEM_METRICS_KEY.format(date=date)
                metrics = redis_conn.lrange(key, 0, -1)
                
                if metrics:
                    # Parse all metrics
                    all_metrics = [json.loads(item.decode()) for item in metrics]
                    
                    # Apply sampling based on interval_minutes
                    if interval_minutes > 1:
                        # Group by intervals
                        interval_seconds = interval_minutes * 60
                        grouped = {}
                        
                        for metric in all_metrics:
                            # Convert timestamp to interval bucket
                            bucket = int(metric["timestamp"] / interval_seconds) * interval_seconds
                            if bucket not in grouped:
                                grouped[bucket] = []
                            grouped[bucket].append(metric)
                        
                        # Take the first entry from each interval
                        sampled_metrics = [group[0] for group in grouped.values()]
                        result[date] = sorted(sampled_metrics, key=lambda x: x["timestamp"])
                    else:
                        result[date] = sorted(all_metrics, key=lambda x: x["timestamp"])
            
            return result
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    @staticmethod
    def get_api_metrics(days: int = 1, endpoints: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get API metrics for the specified endpoints
        
        Args:
            days: Number of days to retrieve data for
            endpoints: Optional list of endpoints to filter by
            
        Returns:
            Dict containing API metrics grouped by endpoint and date
        """
        try:
            redis_conn = get_redis_connection(config.settings)
            
            # Get date range
            end_date = datetime.now()
            date_range = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") 
                         for i in range(days)]
            
            # Get all metrics keys
            all_keys = []
            for key in redis_conn.scan_iter(match="metrics:api:*"):
                key_str = key.decode()
                if endpoints is None or any(endpoint in key_str for endpoint in endpoints):
                    all_keys.append(key_str)
            
            result = {}
            for key in all_keys:
                # Extract endpoint and date from key
                parts = key.split(":")
                if len(parts) < 4:
                    continue
                    
                endpoint = parts[2]
                date = parts[3]
                
                if date not in date_range:
                    continue
                    
                # Get metrics
                raw_metrics = redis_conn.hgetall(key)
                if not raw_metrics:
                    continue
                    
                # Parse metrics
                metrics = {
                    k.decode(): int(v.decode()) if k.decode() != "avg_response_time" else float(v.decode())
                    for k, v in raw_metrics.items()
                }
                
                # Get response times
                response_times = redis_conn.lrange(f"{key}:response_times", 0, -1)
                if response_times:
                    metrics["response_times"] = [float(t.decode()) for t in response_times]
                
                # Organize by endpoint and date
                if endpoint not in result:
                    result[endpoint] = {}
                result[endpoint][date] = metrics
            
            return result
        except Exception as e:
            logger.error(f"Failed to get API metrics: {e}")
            return {}