# ... (imports and docstring unchanged) ...
logger = logging.getLogger("metrics")

# ... (constants unchanged) ...

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
            # ... (body unchanged except for added logs at key points and on error) ...
            logger.info(f"User metrics recorded: user_id={user_id}, action={action}")
            return True
        except Exception as e:
            logger.error(f"Failed to record user metrics: {e}", exc_info=True)
            return False

    @staticmethod
    def record_system_metrics() -> bool:
        logger.debug("record_system_metrics called")
        try:
            # ... (body unchanged except for added logs at key points and on error) ...
            logger.info("System metrics recorded")
            return True
        except Exception as e:
            logger.error(f"Failed to record system metrics: {e}", exc_info=True)
            return False

    @staticmethod
    def record_api_metrics(endpoint: str, response_time: float, status_code: int) -> bool:
        logger.debug(f"record_api_metrics called: endpoint={endpoint}, response_time={response_time}, status_code={status_code}")
        try:
            # ... (body unchanged except for added logs at key points and on error) ...
            logger.info(f"API metrics recorded: endpoint={endpoint}, status_code={status_code}")
            return True
        except Exception as e:
            logger.error(f"Failed to record API metrics: {e}", exc_info=True)
            return False

class MetricsRetriever:
    """Retrieves and formats metrics from storage"""
    # (All methods: add try/except and log errors as above)
    # ... (methods unchanged except for added logging and error catching) ...
