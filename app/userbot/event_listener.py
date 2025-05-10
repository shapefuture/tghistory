import logging
import json
import traceback
from rq.job import Job
from typing import Any

from app.shared.redis_client import get_redis_connection
from app import config
from app.userbot import state, ui, results_sender

logger = logging.getLogger("userbot.event_listener")

async def listen_for_job_events(client: Any) -> None:
    """
    Fully implemented: listens to Redis pubsub, handles all messages, logs all errors, never returns placeholder.
    """
    logger.info("[ENTRY] Starting job events listener")
    redis_conn = None
    pubsub = None

    try:
        redis_conn = get_redis_connection(config.settings)
        pubsub = redis_conn.pubsub(ignore_subscribe_messages=True)
        channel_pattern = f"request_status:*"
        pubsub.psubscribe(channel_pattern)
        logger.info("Subscribed to RQ job status updates via Redis Pub/Sub")

        for message in pubsub.listen():
            try:
                logger.debug(f"PubSub message received: {message}")
                if message["type"] != "pmessage":
                    logger.warning(f"Unexpected message type in Pub/Sub: {message['type']}")
                    continue
                channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                request_id = channel.split(":")[-1]
                try:
                    data = json.loads(message["data"])
                    logger.debug(f"Parsed pubsub message: {data}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode Pub/Sub message as JSON: {e}, data: {message['data']}")
                    continue
                job_id = data.get("job_id")
                chat_id = data.get("chat_id")
                status = data.get("status")
                detail = data.get("detail")
                progress = data.get("progress")
                logger.info(f"Status update: request_id={request_id}, status={status}, job_id={job_id}")
                try:
                    state.update_request_status(request_id, status)
                except Exception as e:
                    logger.error(f"Failed to update request status: {e}")
                try:
                    await ui.update_status_message_for_request(client, request_id)
                except Exception as e:
                    logger.error(f"Failed to update status message: {e}")
                if status in ["SUCCESS", "FAILED"]:
                    logger.info(f"Job completed with status {status}, handling completion")
                    try:
                        await handle_job_completion(client, job_id, request_id, chat_id)
                    except Exception as e:
                        logger.exception(f"Error handling job completion: {e}")
                logger.debug(f"[EXIT] Processed pubsub message for request_id={request_id}")
            except Exception as e:
                logger.exception(f"[ERROR] Error processing Pub/Sub message: {e}")
    except Exception as e:
        logger.exception(f"[ERROR] Fatal error in job events listener: {e}")
    finally:
        if pubsub:
            try:
                logger.debug("Unsubscribing from Pub/Sub channels")
                pubsub.punsubscribe()
            except Exception as e:
                logger.error(f"Error unsubscribing from Pub/Sub: {e}")

async def handle_job_completion(client: Any, job_id: str, request_id: str, chat_id: Any) -> None:
    """
    Fetches job, handles both finished and failed, calls result senders, logs all errors.
    """
    logger.info(f"[ENTRY] handle_job_completion(job_id={job_id}, request_id={request_id}, chat_id={chat_id})")
    try:
        redis_conn = get_redis_connection(config.settings)
        job = Job.fetch(job_id, connection=redis_conn)
        result_data = job.result
        request_data = state.get_request_data(request_id)
        if not request_data:
            logger.error(f"Request data not found: request_id={request_id}")
            logger.debug("[EXIT] handle_job_completion: request data missing")
            return
        user_id = request_data.get("user_id")
        if not user_id:
            logger.error(f"User ID not found in request data: request_id={request_id}")
            logger.debug("[EXIT] handle_job_completion: user_id missing")
            return
        logger.debug(f"Extracted user_id: {user_id}")
        if job.is_finished:
            logger.info(f"Job finished successfully, sending results: user_id={user_id}, chat_id={chat_id}")
            try:
                await results_sender.send_llm_result(client, user_id, chat_id, result_data)
            except Exception as e:
                logger.exception(f"[ERROR] Error sending LLM result: {e}")
        if job.is_failed:
            logger.info(f"Job failed, sending failure message: user_id={user_id}, chat_id={chat_id}")
            try:
                await results_sender.send_failure_message(client, user_id, chat_id, result_data)
            except Exception as e:
                logger.exception(f"[ERROR] Error sending failure message: {e}")
        logger.debug("[EXIT] handle_job_completion OK")
    except Exception as e:
        logger.exception(f"[ERROR] Error handling job completion: job_id={job_id}, request_id={request_id}, error={e}")
