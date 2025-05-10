import logging
import json
import os
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.shared.redis_client import get_redis_connection
from app import config

logger = logging.getLogger("metrics")

# Metric keys
JOB_METRICS_KEY = "metrics:job:{job_id}"
USER_METRICS_KEY = "metrics:user:{user_id}"
SYSTEM_METRICS_KEY = "metrics:system:{date}"
API_METRICS_KEY = "metrics:api:{endpoint}:{date}"

# TTLs
JOB_METRICS_TTL = 60 * 60 * 24 * 7
USER_METRICS_TTL = 60 * 60 * 24 * 31
SYSTEM_METRICS_TTL = 60 * 60 * 24 * 7
API_METRICS_TTL = 60 * 60 * 24 * 31

class MetricsCollector:
    """Collects and stores metrics about system usage and performance"""

    @staticmethod
    def record_job_metrics(job_id: str, metrics: Dict[str, Any]) -> bool:
        logger.debug(f"record_job_metrics called: job_id={job_id}, metrics_keys={list(metrics.keys())}")
        try:
            redis_conn = get_redis_connection(config.settings)
            key = JOB_METRICS_KEY.format(job_id=job_id)
            if "timestamp" not in metrics:
                metrics["timestamp"] = time.time()
            redis_conn.hset(key, mapping={k: json.dumps(v) for k, v in metrics.items()})
            redis_conn.expire(key, JOB_METRICS_TTL)
            logger.info(f"Job metrics recorded: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to record job metrics: {e}", exc_info=True)
            return False

    @staticmethod
    def record_user_metrics(user_id: int, action: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        logger.debug(f"record_user_metrics called: user_id={user_id}, action={action}, metadata={metadata}")
        try:
            redis_conn = get_redis_connection(config.settings)
            key = USER_METRICS_KEY.format(user_id=user_id)
            today = datetime.now().strftime("%Y-%m-%d")
            data = {
                "timestamp": time.time(),
                "action": action
            }
            if metadata:
                data.update(metadata)
            redis_conn.lpush(f"{key}:{today}", json.dumps(data))
            redis_conn.hincrby(f"{key}:counts", action, 1)
            redis_conn.hincrby(f"{key}:counts", f"{action}:{today}", 1)
            redis_conn.expire(f"{key}:{today}", USER_METRICS_TTL)
            redis_conn.expire(f"{key}:counts", USER_METRICS_TTL)
            logger.info(f"User metrics recorded: user_id={user_id}, action={action}")
            return True
        except Exception as e:
            logger.error(f"Failed to record user metrics: {e}", exc_info=True)
            return False

    @staticmethod
    def record_system_metrics() -> bool:
        logger.debug("record_system_metrics called")
        try:
            import psutil
            redis_conn = get_redis_connection(config.settings)
            today = datetime.now().strftime("%Y-%m-%d")
            key = SYSTEM_METRICS_KEY.format(date=today)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.dirname(config.settings.OUTPUT_DIR_PATH))
            worker_count = len([p for p in psutil.process_iter(['pid', 'name', 'cmdline'])
                               if 'python' in p.info['name'] and 'worker' in ' '.join(p.info.get('cmdline', []))])
            data = {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_used_mb": disk.used / (1024 * 1024),
                "active_workers": worker_count,
                "load_avg": os.getloadavg()[0]
            }
            redis_conn.lpush(key, json.dumps(data))
            redis_conn.ltrim(key, 0, 1439)
            redis_conn.expire(key, SYSTEM_METRICS_TTL)
            logger.info("System metrics recorded")
            return True
        except Exception as e:
            logger.error(f"Failed to record system metrics: {e}", exc_info=True)
            return False

    @staticmethod
    def record_api_metrics(endpoint: str, response_time: float, status_code: int) -> bool:
        logger.debug(f"record_api_metrics called: endpoint={endpoint}, response_time={response_time}, status_code={status_code}")
        try:
            redis_conn = get_redis_connection(config.settings)
            today = datetime.now().strftime("%Y-%m-%d")
            key = API_METRICS_KEY.format(endpoint=endpoint, date=today)
            redis_conn.hincrby(key, "total_calls", 1)
            redis_conn.hincrby(key, f"status_{status_code}", 1)
            redis_conn.lpush(f"{key}:response_times", response_time)
            redis_conn.ltrim(f"{key}:response_times", 0, 999)
            current_count = int(redis_conn.hget(key, "total_calls") or 0)
            current_avg = float(redis_conn.hget(key, "avg_response_time") or 0)
            if current_count == 1:
                new_avg = response_time
            else:
                new_avg = ((current_avg * (current_count - 1)) + response_time) / current_count
            redis_conn.hset(key, "avg_response_time", new_avg)
            redis_conn.expire(key, API_METRICS_TTL)
            redis_conn.expire(f"{key}:response_times", API_METRICS_TTL)
            logger.info(f"API metrics recorded: endpoint={endpoint}, status_code={status_code}")
            return True
        except Exception as e:
            logger.error(f"Failed to record API metrics: {e}", exc_info=True)
            return False

class MetricsRetriever:
    @staticmethod
    def get_job_metrics(job_id: str) -> Dict[str, Any]:
        logger.debug(f"get_job_metrics called: job_id={job_id}")
        try:
            redis_conn = get_redis_connection(config.settings)
            key = JOB_METRICS_KEY.format(job_id=job_id)
            raw_metrics = redis_conn.hgetall(key)
            if not raw_metrics:
                logger.info(f"No metrics found for job_id={job_id}")
                return {}
            result = {k.decode(): json.loads(v.decode()) for k, v in raw_metrics.items()}
            logger.info(f"Job metrics retrieved: job_id={job_id}, keys={list(result.keys())}")
            return result
        except Exception as e:
            logger.error(f"Failed to get job metrics: {e}", exc_info=True)
            return {}

    @staticmethod
    def get_user_metrics(user_id: int, days: int = 7, actions: Optional[List[str]] = None) -> Dict[str, Any]:
        logger.debug(f"get_user_metrics called: user_id={user_id}, days={days}, actions={actions}")
        try:
            redis_conn = get_redis_connection(config.settings)
            key_prefix = USER_METRICS_KEY.format(user_id=user_id)
            end_date = datetime.now()
            date_range = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
            counts_key = f"{key_prefix}:counts"
            raw_counts = redis_conn.hgetall(counts_key)
            counts = {
                k.decode(): int(v.decode())
                for k, v in raw_counts.items()
                if actions is None or any(action in k.decode() for action in actions)
            }
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
            logger.info(f"User metrics retrieved: user_id={user_id}")
            return {
                "counts": counts,
                "daily_activity": daily_activity
            }
        except Exception as e:
            logger.error(f"Failed to get user metrics: {e}", exc_info=True)
            return {}

    @staticmethod
    def get_system_metrics(days: int = 1, interval_minutes: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        logger.debug(f"get_system_metrics called: days={days}, interval_minutes={interval_minutes}")
        try:
            redis_conn = get_redis_connection(config.settings)
            end_date = datetime.now()
            date_range = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
            result = {}
            for date in date_range:
                key = SYSTEM_METRICS_KEY.format(date=date)
                metrics = redis_conn.lrange(key, 0, -1)
                if metrics:
                    all_metrics = [json.loads(item.decode()) for item in metrics]
                    if interval_minutes > 1:
                        interval_seconds = interval_minutes * 60
                        grouped = {}
                        for metric in all_metrics:
                            bucket = int(metric["timestamp"] / interval_seconds) * interval_seconds
                            if bucket not in grouped:
                                grouped[bucket] = []
                            grouped[bucket].append(metric)
                        sampled_metrics = [group[0] for group in grouped.values()]
                        result[date] = sorted(sampled_metrics, key=lambda x: x["timestamp"])
                    else:
                        result[date] = sorted(all_metrics, key=lambda x: x["timestamp"])
            logger.info("System metrics retrieved")
            return result
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}", exc_info=True)
            return {}

    @staticmethod
    def get_api_metrics(days: int = 1, endpoints: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        logger.debug(f"get_api_metrics called: days={days}, endpoints={endpoints}")
        try:
            redis_conn = get_redis_connection(config.settings)
            end_date = datetime.now()
            date_range = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
            all_keys = []
            for key in redis_conn.scan_iter(match="metrics:api:*"):
                key_str = key.decode()
                if endpoints is None or any(endpoint in key_str for endpoint in endpoints):
                    all_keys.append(key_str)
            result = {}
            for key in all_keys:
                parts = key.split(":")
                if len(parts) < 4:
                    continue
                endpoint = parts[2]
                date = parts[3]
                if date not in date_range:
                    continue
                raw_metrics = redis_conn.hgetall(key)
                if not raw_metrics:
                    continue
                metrics = {
                    k.decode(): int(v.decode()) if k.decode() != "avg_response_time" else float(v.decode())
                    for k, v in raw_metrics.items()
                }
                response_times = redis_conn.lrange(f"{key}:response_times", 0, -1)
                if response_times:
                    metrics["response_times"] = [float(t.decode()) for t in response_times]
                if endpoint not in result:
                    result[endpoint] = {}
                result[endpoint][date] = metrics
            logger.info("API metrics retrieved")
            return result
        except Exception as e:
            logger.error(f"Failed to get API metrics: {e}", exc_info=True)
            return {}
