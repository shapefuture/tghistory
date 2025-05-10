import logging
import structlog
import sys

def setup_logging(settings):
    try:
        logging.basicConfig(
            level=getattr(logging, getattr(settings, "LOG_LEVEL", "INFO").upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s [%(process)d]: %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.LOG_LEVEL)),
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ]
        )
        logging.getLogger().info("Structured logging initialized successfully")
    except Exception as e:
        logging.basicConfig(level="ERROR")
        logging.error(f"Falling back to basic logging due to error: {e}", exc_info=True)
