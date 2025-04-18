import logging
import json
import time
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
    redis_conn = get_redis_connection(config.settings)
    
    # Track performance metrics
    metrics = {
        "start_time": time.time(),
        "message_count": 0,
        "extract_time": 0,
        "llm_time": 0,
        "total_time": 0,
        "chat_id": chat_id,
        "user_id": user_id,
        "request_id": request_id,
    }

    def publish_status(status: str, detail: Optional[str] = None, progress: Optional[int] = None):
        msg = {
            "job_id": job.id if job else None,
            "chat_id": chat_id,
            "status": status,
            "detail": detail,
            "progress": progress,
        }
        try:
            redis_conn.publish(f"request_status:{request_id}", json.dumps(msg))
        except Exception as e:
            logger.error(f"Failed to publish status update: {e}")

    try:
        from rq import get_current_job
        job = get_current_job()
        
        # Record job started in metrics
        MetricsCollector.record_user_metrics(
            user_id, 
            "job_started", 
            {"chat_id": chat_id, "request_id": request_id, "job_id": job.id if job else None}
        )
        
        publish_status('STARTED')

        # Connect Telethon session
        client = TelegramClient(user_session_path, config.settings.TELEGRAM_API_ID, config.settings.TELEGRAM_API_HASH)
        client.connect()
        if not client.is_user_authorized():
            publish_status('FAILED', detail="User not authorized.")
            
            # Record authentication failure in metrics
            metrics["error"] = "User not authorized"
            metrics["total_time"] = time.time() - metrics["start_time"]
            MetricsCollector.record_job_metrics(job.id if job else "unknown", metrics)
            
            return {"status": "FAILURE", "error": "User not authorized."}

        # Start message extraction
        extract_start = time.time()
        publish_status('EXTRACTING_HISTORY')
        history = []
        count = 0

        try:
            for msg in client.iter_messages(chat_id, reverse=True):
                text = getattr(msg, "text", "")
                if text:
                    cleaned = clean_message_text(text)
                    if cleaned:
                        history.append(cleaned)
                    count += 1
                    if count % 100 == 0:
                        publish_status('PROGRESS', detail=f"{count} messages", progress=count)
                        
                        # Periodically update metrics during extraction
                        if count % 500 == 0:
                            current_metrics = {
                                "message_count": count,
                                "extract_time": time.time() - extract_start,
                                "status": "EXTRACTING"
                            }
                            MetricsCollector.record_job_metrics(
                                job.id if job else "unknown", current_metrics
                            )
        except FloodWaitError as fw:
            import time
            logger.warning(f"FloodWait: Sleeping {fw.seconds}s")
            publish_status('WAITING', detail=f"Flood wait: {fw.seconds}s")
            time.sleep(fw.seconds)
        
        metrics["message_count"] = count
        metrics["extract_time"] = time.time() - extract_start
        
        history_text = "\n".join(history)
        participants_text = None

        # (Optional) Group participant extraction
        entity = client.get_entity(chat_id)
        if hasattr(entity, "participants_count") and entity.participants_count:
            try:
                publish_status('EXTRACTING_PARTICIPANTS')
                parts = []
                participant_count = 0
                for user in client.get_participants(chat_id):
                    parts.append(f"{user.id}\t{user.first_name} {user.last_name or ''} @{user.username or ''}".strip())
                    participant_count += 1
                
                participants_text = "\n".join(parts)
                metrics["participant_count"] = participant_count
            except Exception as e:
                logger.error(f"Participant extraction error: {e}")
                metrics["participant_error"] = str(e)

        client.disconnect()

        if not history_text:
            error_msg = "No text history extracted."
            publish_status('FAILED', detail=error_msg)
            
            # Record error in metrics
            metrics["error"] = error_msg
            metrics["total_time"] = time.time() - metrics["start_time"]
            MetricsCollector.record_job_metrics(job.id if job else "unknown", metrics)
            
            raise ValueError(error_msg)

        # Start LLM processing
        llm_start = time.time()
        publish_status('CALLING_LLM')
        import asyncio
        
        # Call LLM with retries for network issues
        summary = asyncio.run(get_llm_summary(custom_prompt, history_text, config.settings))
        
        metrics["llm_time"] = time.time() - llm_start
        
        if not summary:
            error_msg = "LLM summarization failed."
            publish_status('FAILED', detail=error_msg)
            
            # Record error in metrics
            metrics["error"] = error_msg 
            metrics["total_time"] = time.time() - metrics["start_time"]
            MetricsCollector.record_job_metrics(job.id if job else "unknown", metrics)
            
            raise RuntimeError(error_msg)

        participants_file = None
        if participants_text:
            import uuid
            import os
            fname = f"participants_{request_id}_{chat_id}_{uuid.uuid4().hex}.txt"
            fpath = os.path.join(config.settings.OUTPUT_DIR_PATH, fname)
            try:
                with open(fpath, "w") as fp:
                    fp.write(participants_text)
                participants_file = fpath
            except Exception as e:
                logger.error(f"Writing participants file error: {e}")
                metrics["file_error"] = str(e)
        
        publish_status('SUCCESS')
        
        # Record final metrics
        metrics["total_time"] = time.time() - metrics["start_time"]
        metrics["has_participants_file"] = participants_file is not None
        metrics["summary_length"] = len(summary)
        MetricsCollector.record_job_metrics(job.id if job else "unknown", metrics)
        
        # Record successful completion in user metrics
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
        logger.exception(f"Task error: {e}")
        error_message = f"{type(e).__name__}: {str(e)}"
        publish_status('FAILED', detail=error_message)
        
        # Record error in metrics
        if metrics.get("total_time") == 0:
            metrics["total_time"] = time.time() - metrics["start_time"]
        metrics["error"] = error_message
        MetricsCollector.record_job_metrics(job.id if job else "unknown", metrics)
        
        # Record failure in user metrics
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
        
        # Check if exception is retryable, and if so, let retry decorator handle it
        if is_retryable_exception(e) and not getattr(e, "_already_retried", False):
            # Mark exception as already being retried to prevent infinite retries
            # if retry decorator is not catching it for some reason
            setattr(e, "_already_retried", True)
            raise e
        
        return {"status": "FAILURE", "error": error_message}