import logging
import json
from rq.job import Job

from app.shared.redis_client import get_redis_connection
from app import config
from app.userbot import state, ui, results_sender

logger = logging.getLogger("userbot.event_listener")

async def listen_for_job_events(client):
    redis_conn = get_redis_connection(config.settings)
    pubsub = redis_conn.pubsub(ignore_subscribe_messages=True)
    pubsub.psubscribe(f"request_status:*")
    logger.info("Subscribed to RQ job status updates via Redis Pub/Sub.")

    for message in pubsub.listen():
        if message["type"] == "pmessage":
            try:
                data = json.loads(message["data"])
                request_id = message["channel"].decode().split(":")[-1]
                job_id = data.get("job_id")
                chat_id = data.get("chat_id")
                status = data.get("status")
                detail = data.get("detail")
                progress = data.get("progress")
                logger.debug(f"Received status update: {data}")
                state.update_request_status(request_id, status)
                # Show progress to user via UI
                await ui.update_status_message_for_request(client, request_id)
                if status in ["SUCCESS", "FAILED"]:
                    await handle_job_completion(client, job_id, request_id, chat_id)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode Pub/Sub message: {message['data']}")
            except Exception as e:
                logger.exception(f"Error processing Pub/Sub message: {e}")

async def handle_job_completion(client, job_id, request_id, chat_id):
    redis_conn = get_redis_connection(config.settings)
    job = Job.fetch(job_id, connection=redis_conn)
    result_data = job.result
    user_id = state.get_request_data(request_id).get("user_id")
    if job.is_finished:
        await results_sender.send_llm_result(client, user_id, chat_id, result_data)
    if job.is_failed:
        await results_sender.send_failure_message(client, user_id, chat_id, result_data)
    # Optional: update overall request status/cleanup if all jobs for this request are finished