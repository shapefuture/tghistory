import logging
import sys
import signal
import time

from app.logging_config import setup_logging
from app import config
from app.shared.redis_client import get_redis_connection, get_rq_queue
from app.worker import tasks

from rq import Worker

logger = logging.getLogger("worker")

def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals gracefully"""
    signal_name = {
        signal.SIGINT: "SIGINT",
        signal.SIGTERM: "SIGTERM",
    }.get(signum, str(signum))
    
    logger.info(f"Received {signal_name} signal. Shutting down gracefully...")
    # Wait a moment to allow current job to complete
    time.sleep(1)
    sys.exit(0)

def main():
    try:
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
        
        setup_logging(config.settings)
        redis_conn = get_redis_connection(config.settings)
        queue = get_rq_queue(redis_conn, config.settings)
        
        # Log startup information
        logger.info(f"Starting worker for queue: {queue.name}")
        logger.info(f"Redis connection: {redis_conn}")
        
        worker = Worker(
            [queue],
            connection=redis_conn,
            exception_handlers=[]
        )
        
        # Set worker name for better identification in logs
        worker.name = f"worker.{os.getpid()}.{time.time()}"
        logger.info(f"Worker {worker.name} started")
        
        # Start the worker
        worker.work()
    except Exception as e:
        logger.critical(f"Worker startup failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    import os  # Import needed for PID in worker name
    main()