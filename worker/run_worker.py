import logging
import sys

from app.logging_config import setup_logging
from app import config
from app.shared.redis_client import get_redis_connection, get_rq_queue
from app.worker import tasks

from rq import Worker

def main():
    try:
        setup_logging(config.settings)
        redis_conn = get_redis_connection(config.settings)
        queue = get_rq_queue(redis_conn, config.settings)
        Worker(
            [queue],
            connection=redis_conn,
            exception_handlers=[]
        ).work()
    except Exception as e:
        logging.critical(f"Worker startup failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()