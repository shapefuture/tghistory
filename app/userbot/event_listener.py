import logging
import json
import traceback
from rq.job import Job
from typing import Optional, Dict, Any

from app.shared.redis_client import get_redis_connection
from app import config
from app.userbot import state, ui, results_sender

logger = logging.getLogger("userbot.event_listener")

async def listen_for_job_events(client):
    """
    Subscribe to Redis Pub/Sub for job status updates
    
    Args:
        client: Telethon client instance
    """
    logger.info("Starting job events listener")
    redis_conn = None
    pubsub = None
    
    try:
        # Connect to Redis
        logger.debug("Getting Redis connection")
        redis_conn = get_redis_connection(config.settings)
        
        # Create PubSub object
        logger.debug("Creating Redis Pub/Sub")
        pubsub = redis_conn.pubsub(ignore_subscribe_messages=True)
        
        # Subscribe to request status channels
        channel_pattern = f"request_status:*"
        logger.debug(f"Subscribing to channel pattern: {channel_pattern}")
        pubsub.psubscribe(channel_pattern)
        
        logger.info("Subscribed to RQ job status updates via Redis Pub/Sub")

        # Process incoming messages
        for message in pubsub.listen():
            try:
                # Check message type
                if message["type"] != "pmessage":
                    logger.warning(f"Unexpected message type in Pub/Sub: {message['type']}")
                    continue
                
                # Parse channel and data
                channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                logger.debug(f"Received message on channel: {channel}")
                
                # Extract request ID from channel
                request_id = channel.split(":")[-1]
                logger.debug(f"Extracted request_id: {request_id}")
                
                # Parse JSON data
                try:
                    data = json.loads(message["data"])
                    logger.debug(f"Parsed message data: {data}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode Pub/Sub message as JSON: {e}, data: {message['data']}")
                    continue
                
                # Extract message fields
                job_id = data.get("job_id")
                chat_id = data.get("chat_id")
                status = data.get("status")
                detail = data.get("detail")
                progress = data.get("progress")
                
                logger.info(f"Status update: request_id={request_id}, status={status}, job_id={job_id}")
                
                # Update request status in Redis
                try:
                    logger.debug(f"Updating request status: request_id={request_id}, status={status}")
                    state.update_request_status(request_id, status)
                except Exception as e:
                    logger.error(f"Failed to update request status: {e}")
                
                # Update UI with status
                try:
                    logger.debug(f"Updating status message for request: {request_id}")
                    await ui.update_status_message_for_request(client, request_id)
                except Exception as e:
                    logger.error(f"Failed to update status message: {e}")
                
                # Handle job completion
                if status in ["SUCCESS", "FAILED"]:
                    logger.info(f"Job completed with status {status}, handling completion")
                    try:
                        await handle_job_completion(client, job_id, request_id, chat_id)
                    except Exception as e:
                        logger.exception(f"Error handling job completion: {e}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode Pub/Sub message: {e}, message: {message}")
            except Exception as e:
                logger.exception(f"Error processing Pub/Sub message: {e}")
    except Exception as e:
        logger.exception(f"Fatal error in job events listener: {e}")
    finally:
        # Clean up
        if pubsub:
            try:
                logger.debug("Unsubscribing from Pub/Sub channels")
                pubsub.punsubscribe()
            except Exception as e:
                logger.error(f"Error unsubscribing from Pub/Sub: {e}")

async def handle_job_completion(client, job_id: str, request_id: str, chat_id):
    """
    Handle completed job (fetch results and send to user)
    
    Args:
        client: Telethon client instance
        job_id: RQ job ID
        request_id: Request ID 
        chat_id: Target chat ID
    """
    logger.info(f"Handling job completion: job_id={job_id}, request_id={request_id}")
    
    try:
        # Get Redis connection
        logger.debug("Getting Redis connection")
        redis_conn = get_redis_connection(config.settings)
        
        # Fetch job
        logger.debug(f"Fetching RQ job: job_id={job_id}")
        job = Job.fetch(job_id, connection=redis_conn)
        
        # Get result data
        result_data = job.result
        logger.debug(f"Job result data: {result_data}")
        
        # Get user ID from request data
        logger.debug(f"Getting request data: request_id={request_id}")
        request_data = state.get_request_data(request_id)
        
        if not request_data:
            logger.error(f"Request data not found: request_id={request_id}")
            return
            
        user_id = request_data.get("user_id")
        
        if not user_id:
            logger.error(f"User ID not found in request data: request_id={request_id}")
            return
            
        logger.debug(f"Extracted user_id: {user_id}")
        
        # Handle based on job status
        if job.is_finished:
            logger.info(f"Job finished successfully, sending results: user_id={user_id}, chat_id={chat_id}")
            try:
                await results_sender.send_llm_result(client, user_id, chat_id, result_data)
            except Exception as e:
                logger.exception(f"Error sending LLM result: {e}")
                
        if job.is_failed:
            logger.info(f"Job failed, sending failure message: user_id={user_id}, chat_id={chat_id}")
            try:
                await results_sender.send_failure_message(client, user_id, chat_id, result_data)
            except Exception as e:
                logger.exception(f"Error sending failure message: {e}")
    except Exception as e:
        logger.exception(f"Error handling job completion: job_id={job_id}, request_id={request_id}, error={e}")