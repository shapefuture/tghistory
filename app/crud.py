import logging
from typing import Optional
from app.shared.redis_client import get_redis_connection
from app import config
from app.schemas import ProcessingRequestSchema, TaskStatusSchema

logger = logging.getLogger("crud")

def get_processing_request(request_id: str) -> Optional[ProcessingRequestSchema]:
    logger.debug(f"get_processing_request called: request_id={request_id}")
    try:
        redis_conn = get_redis_connection(config.settings)
        key = f"request:{request_id}:data"
        data = redis_conn.hgetall(key)
        if not data:
            logger.warning(f"No processing request found in Redis: {key}")
            return None
        try:
            # decode bytes
            decoded = {k.decode(): v.decode() for k, v in data.items()}
            logger.debug(f"Decoded processing request: {decoded}")
        except Exception as decode_error:
            logger.error(f"Failed to decode Redis result for {key}: {decode_error}", exc_info=True)
            return None
        try:
            # Build schema and log validation
            req = ProcessingRequestSchema(**decoded)
            logger.info(f"ProcessingRequestSchema built for request_id={request_id}")
            return req
        except Exception as schema_error:
            logger.error(f"Failed to create ProcessingRequestSchema: {schema_error}", exc_info=True)
            return None
    except Exception as e:
        logger.error(f"get_processing_request error: {e}", exc_info=True)
        return None

def get_task_status(request_id: str) -> Optional[TaskStatusSchema]:
    logger.debug(f"get_task_status called: request_id={request_id}")
    try:
        redis_conn = get_redis_connection(config.settings)
        key = f"request:{request_id}:data"
        data = redis_conn.hgetall(key)
        if not data:
            logger.warning(f"No task status found in Redis: {key}")
            return None
        try:
            decoded = {k.decode(): v.decode() for k, v in data.items()}
            logger.debug(f"Decoded task status: {decoded}")
        except Exception as decode_error:
            logger.error(f"Failed to decode Redis result for {key}: {decode_error}", exc_info=True)
            return None
        try:
            status = TaskStatusSchema(**decoded)
            logger.info(f"TaskStatusSchema built for request_id={request_id}")
            return status
        except Exception as schema_error:
            logger.error(f"Failed to create TaskStatusSchema: {schema_error}", exc_info=True)
            return None
    except Exception as e:
        logger.error(f"get_task_status error: {e}", exc_info=True)
        return None
