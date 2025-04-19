import logging
import json
import time
import os
import traceback
import asyncio
import uuid
from typing import Optional, Dict, Any

from app.shared.redis_client import get_redis_connection
from app.worker.llm_service import get_llm_summary
from app.worker.utils import clean_message_text
from app.shared.retry import retry, async_retry, is_retryable_exception
from app.shared.metrics import MetricsCollector
from app import config

from telethon.sync import TelegramClient
from telethon.errors.rpcerrorlist import FloodWaitError

logger = logging.getLogger("worker.tasks")

@retry(
    max_tries=3,
    delay=2.0,
    backoff=2.0,
    exceptions=(Exception,),
    jitter=True,
    on_retry=lambda e, i, d: logger.warning(f"Retrying job due to error: {e}")
)
def extract_and_summarize_data(chat_id, user_session_path, user_id, request_id, custom_prompt):
    """
    Extract chat history and generate LLM summary
    
    This function is the main RQ job that:
    1. Connects to Telegram using the user's session
    2. Extracts message history from the target chat
    3. Extracts participants list if applicable
    4. Calls LLM for summarization
    5. Saves results and publishes status updates
    
    The function includes automatic retries for transient errors.
    
    Args:
        chat_id: Target chat ID to extract from
        user_session_path: Path to Telethon session file
        user_id: ID of requesting user
        request_id: Unique request identifier
        custom_prompt: User-provided prompt for LLM
        
    Returns:
        Dict containing job results or error information
    """
    job = None
    redis_conn = None
    client = None
    
    # Start time tracking
    overall_start_time = time.time()
    logger.info(f"Starting extraction job: request_id={request_id}, chat_id={chat_id}, user_id={user_id}")
    
    # Track performance metrics
    metrics = {
        "start_time": overall_start_time,
        "message_count": 0,
        "extract_time": 0,
        "llm_time": 0,
        "total_time": 0,
        "chat_id": chat_id,
        "user_id": user_id,
        "request_id": request_id,
    }

    def publish_status(status: str, detail: Optional[str] = None, progress: Optional[int] = None):
        """Publish job status update to Redis Pub/Sub"""
        try:
            if not redis_conn:
                logger.error("Cannot publish status: Redis connection not initialized")
                return
                
            msg = {
                "job_id": job.id if job else None,
                "chat_id": chat_id,
                "status": status,
                "detail": detail,
                "progress": progress,
                "timestamp": time.time()
            }
            
            channel = f"request_status:{request_id}"
            message = json.dumps(msg)
            
            logger.debug(f"Publishing status update: channel={channel}, status={status}, detail={detail}")
            redis_conn.publish(channel, message)
            logger.debug("Status update published successfully")
        except Exception as e:
            logger.error(f"Failed to publish status update: status={status}, error={e}")

    try:
        # Get current RQ job
        try:
            from rq import get_current_job
            job = get_current_job()
            logger.debug(f"Retrieved current RQ job: id={job.id if job else 'unknown'}")
        except Exception as job_error:
            logger.error(f"Error getting current job: {job_error}")
        
        # Get Redis connection
        try:
            logger.debug("Connecting to Redis...")
            redis_conn = get_redis_connection(config.settings)
            logger.debug("Redis connection established")
        except Exception as redis_error:
            logger.error(f"Failed to connect to Redis: {redis_error}")
            raise
        
        # Record job started in metrics
        try:
            logger.debug("Recording job start metrics")
            MetricsCollector.record_user_metrics(
                user_id, 
                "job_started", 
                {"chat_id": chat_id, "request_id": request_id, "job_id": job.id if job else None}
            )
        except Exception as metrics_error:
            logger.error(f"Failed to record job start metrics: {metrics_error}")
        
        # Publish initial status
        publish_status('STARTED')

        # Connect to Telegram
        logger.debug(f"Connecting to Telegram: session_path={user_session_path}")
        client = TelegramClient(user_session_path, config.settings.TELEGRAM_API_ID, config.settings.TELEGRAM_API_HASH)
        
        try:
            logger.debug("Establishing connection to Telegram...")
            client.connect()
            
            logger.debug("Checking authorization...")
            if not client.is_user_authorized():
                logger.error("User is not authorized")
                publish_status('FAILED', detail="User not authorized.")
                
                # Record authentication failure in metrics
                metrics["error"] = "User not authorized"
                metrics["total_time"] = time.time() - metrics["start_time"]
                MetricsCollector.record_job_metrics(job.id if job else "unknown", metrics)
                
                return {"status": "FAILURE", "error": "User not authorized."}
                
            logger.info("Successfully connected to Telegram and authorized")
        except Exception as auth_error:
            logger.exception(f"Failed to connect/authenticate to Telegram: {auth_error}")
            publish_status('FAILED', detail=f"Telegram connection error: {str(auth_error)}")
            
            metrics["error"] = f"Telegram connection error: {str(auth_error)}"
            metrics["total_time"] = time.time() - metrics["start_time"]
            MetricsCollector.record_job_metrics(job.id if job else "unknown", metrics)
            
            raise

        # Start message extraction
        extract_start = time.time()
        logger.info(f"Starting message extraction: chat_id={chat_id}")
        publish_status('EXTRACTING_HISTORY')
        
        history = []
        count = 0

        try:
            logger.debug(f"Iterating messages: chat_id={chat_id}")
            for msg in client.iter_messages(chat_id, reverse=True):
                text = getattr(msg, "text", "")
                if text:
                    try:
                        cleaned = clean_message_text(text)
                        if cleaned:
                            history.append(cleaned)
                    except Exception as clean_error:
                        logger.warning(f"Error cleaning message text: {clean_error}")
                        
                    count += 1
                    if count % 100 == 0:
                        logger.debug(f"Extraction progress: {count} messages")
                        publish_status('PROGRESS', detail=f"{count} messages", progress=count)
                        
                        # Periodically update metrics during extraction
                        if count % 500 == 0:
                            try:
                                current_metrics = {
                                    "message_count": count,
                                    "extract_time": time.time() - extract_start,
                                    "status": "EXTRACTING"
                                }
                                MetricsCollector.record_job_metrics(
                                    job.id if job else "unknown", current_metrics
                                )
                            except Exception as metrics_error:
                                logger.error(f"Failed to update extraction metrics: {metrics_error}")
        except FloodWaitError as fw:
            logger.warning(f"Telegram FloodWaitError: Must wait {fw.seconds}s")
            publish_status('WAITING', detail=f"Flood wait: {fw.seconds}s")
            
            try:
                logger.info(f"Sleeping for {fw.seconds} seconds due to FloodWaitError")
                time.sleep(fw.seconds)
                logger.info("Resuming after FloodWaitError timeout")
            except Exception as sleep_error:
                logger.error(f"Error during FloodWaitError sleep: {sleep_error}")
                
        except Exception as extract_error:
            logger.exception(f"Error extracting messages: {extract_error}")
            publish_status('FAILED', detail=f"Extraction error: {str(extract_error)}")
            raise
        
        # Update extraction metrics
        extract_duration = time.time() - extract_start
        metrics["message_count"] = count
        metrics["extract_time"] = extract_duration
        
        logger.info(f"Message extraction completed: count={count}, time={extract_duration:.2f}s")
        
        # Join extracted messages into text
        if not history:
            logger.warning("No message history extracted")
            history_text = ""
        else:
            history_text = "\n".join(history)
            logger.debug(f"Joined history text: length={len(history_text)}")
        
        # Extract participants (for groups)
        participants_text = None
        try:
            logger.debug(f"Getting chat entity: chat_id={chat_id}")
            entity = client.get_entity(chat_id)
            
            if hasattr(entity, "participants_count") and entity.participants_count:
                logger.info(f"Extracting participants: chat_id={chat_id}, count={entity.participants_count}")
                publish_status('EXTRACTING_PARTICIPANTS')
                
                parts = []
                participant_count = 0
                
                logger.debug("Iterating participants")
                for user in client.get_participants(chat_id):
                    parts.append(f"{user.id}\t{user.first_name} {user.last_name or ''} @{user.username or ''}".strip())
                    participant_count += 1
                    
                    if participant_count % 100 == 0:
                        logger.debug(f"Extracted {participant_count} participants")
                
                participants_text = "\n".join(parts)
                logger.info(f"Participants extraction completed: count={participant_count}")
                metrics["participant_count"] = participant_count
            else:
                logger.info("Chat doesn't have participants (not a group/channel or no access)")
        except Exception as e:
            logger.error(f"Participant extraction error: {e}")
            metrics["participant_error"] = str(e)

        # Disconnect from Telegram
        try:
            logger.debug("Disconnecting from Telegram")
            client.disconnect()
            logger.debug("Telegram disconnected")
        except Exception as disconnect_error:
            logger.warning(f"Error disconnecting from Telegram: {disconnect_error}")

        # Check if we have any history
        if not history_text:
            error_msg = "No text history extracted."
            logger.error(error_msg)
            publish_status('FAILED', detail=error_msg)
            
            # Record error in metrics
            metrics["error"] = error_msg
            metrics["total_time"] = time.time() - metrics["start_time"]
            MetricsCollector.record_job_metrics(job.id if job else "unknown", metrics)
            
            raise ValueError(error_msg)

        # Start LLM processing
        llm_start = time.time()
        logger.info("Starting LLM summarization")
        publish_status('CALLING_LLM')
        
        try:
            # Call LLM with retries for network issues
            logger.debug(f"Calling LLM API: prompt_length={len(custom_prompt)}, history_length={len(history_text)}")
            summary = asyncio.run(get_llm_summary(custom_prompt, history_text, config.settings))
            
            llm_duration = time.time() - llm_start
            metrics["llm_time"] = llm_duration
            
            logger.info(f"LLM summarization completed: summary_length={len(summary) if summary else 0}, time={llm_duration:.2f}s")
            
            if not summary:
                error_msg = "LLM summarization failed (empty result)."
                logger.error(error_msg)
                publish_status('FAILED', detail=error_msg)
                
                # Record error in metrics
                metrics["error"] = error_msg 
                metrics["total_time"] = time.time() - metrics["start_time"]
                MetricsCollector.record_job_metrics(job.id if job else "unknown", metrics)
                
                raise RuntimeError(error_msg)
        except Exception as llm_error:
            logger.exception(f"LLM summarization error: {llm_error}")
            publish_status('FAILED', detail=f"LLM error: {str(llm_error)}")
            raise

        # Save participants to file if available
        participants_file = None
        if participants_text:
            try:
                logger.debug("Saving participants to file")
                import uuid
                import os
                
                # Generate unique filename
                fname = f"participants_{request_id}_{chat_id}_{uuid.uuid4().hex}.txt"
                fpath = os.path.join(config.settings.OUTPUT_DIR_PATH, fname)
                
                logger.debug(f"Writing participants file: path={fpath}")
                with open(fpath, "w") as fp:
                    fp.write(participants_text)
                    
                participants_file = fpath
                logger.info(f"Participants file saved: path={fpath}")
            except Exception as e:
                logger.error(f"Error writing participants file: {e}")
                metrics["file_error"] = str(e)
        
        # Publish success status
        publish_status('SUCCESS')
        
        # Record final metrics
        overall_duration = time.time() - overall_start_time
        metrics["total_time"] = overall_duration
        metrics["has_participants_file"] = participants_file is not None
        metrics["summary_length"] = len(summary)
        
        try:
            logger.debug("Recording final job metrics")
            MetricsCollector.record_job_metrics(job.id if job else "unknown", metrics)
        except Exception as metrics_error:
            logger.error(f"Failed to record final job metrics: {metrics_error}")
        
        # Record successful completion in user metrics
        try:
            logger.debug("Recording job completion in user metrics")
            MetricsCollector.record_user_metrics(
                user_id, 
                "job_completed", 
                {
                    "chat_id": chat_id, 
                    "request_id": request_id,
                    "message_count": count,
                    "processing_time": metrics["total_time"]
                }
            )
        except Exception as metrics_error:
            logger.error(f"Failed to record user completion metrics: {metrics_error}")
        
        logger.info(f"Job completed successfully: request_id={request_id}, time={overall_duration:.2f}s")
        
        # Return results
        return {
            "status": "SUCCESS",
            "summary": summary,
            "participants_file": participants_file,
            "request_id": request_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "metrics": {
                "message_count": count,
                "extract_time_seconds": round(metrics["extract_time"], 2),
                "llm_time_seconds": round(metrics["llm_time"], 2),
                "total_time_seconds": round(metrics["total_time"], 2)
            }
        }
    except Exception as e:
        # Capture the full stack trace
        error_traceback = traceback.format_exc()
        logger.exception(f"Task error: {e}")
        error_message = f"{type(e).__name__}: {str(e)}"
        
        try:
            publish_status('FAILED', detail=error_message)
        except Exception as status_error:
            logger.error(f"Failed to publish failure status: {status_error}")
        
        # Record error in metrics
        if metrics.get("total_time") == 0:
            metrics["total_time"] = time.time() - metrics["start_time"]
        metrics["error"] = error_message
        metrics["traceback"] = error_traceback
        
        try:
            MetricsCollector.record_job_metrics(job.id if job else "unknown", metrics)
        except Exception as metrics_error:
            logger.error(f"Failed to record error metrics: {metrics_error}")
        
        # Record failure in user metrics
        try:
            MetricsCollector.record_user_metrics(
                user_id, 
                "job_failed", 
                {
                    "chat_id": chat_id, 
                    "request_id": request_id,
                    "error": error_message,
                    "processing_time": metrics["total_time"]
                }
            )
        except Exception as metrics_error:
            logger.error(f"Failed to record user failure metrics: {metrics_error}")
        
        # Check if exception is retryable, and if so, let retry decorator handle it
        if is_retryable_exception(e) and not getattr(e, "_already_retried", False):
            # Mark exception as already being retried to prevent infinite retries
            # if retry decorator is not catching it for some reason
            setattr(e, "_already_retried", True)
            logger.info(f"Error is retryable: {error_message}")
            raise e
        
        logger.error(f"Job failed: request_id={request_id}, error={error_message}")
        
        return {
            "status": "FAILURE", 
            "error": error_message,
            "traceback": error_traceback[:1000],  # Include part of traceback for debugging
            "request_id": request_id,
            "user_id": user_id,
            "chat_id": chat_id,
        }
    finally:
        # Ensure client is disconnected
        if client and client.is_connected():
            try:
                logger.debug("Disconnecting Telegram client in finally block")
                client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting client in finally: {e}")