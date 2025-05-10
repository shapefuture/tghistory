import os
import logging
import traceback
import time
from typing import Any, Dict

logger = logging.getLogger("userbot.results_sender")

async def send_llm_result(client: Any, user_id: int, chat_id: int, job_result_dict: Dict[str, Any]) -> None:
    """
    Sends summary in chunks, metrics, participant file, robust error handling/logging.
    """
    logger.debug(f"[ENTRY] send_llm_result(user_id={user_id}, chat_id={chat_id}, keys={list(job_result_dict.keys()) if isinstance(job_result_dict, dict) else type(job_result_dict)})")
    try:
        if not isinstance(job_result_dict, dict):
            logger.error(f"Invalid job result (not a dict): {type(job_result_dict)}")
            await client.send_message(user_id, f"❌ Invalid job result format. Please contact support.")
            return
        summary = job_result_dict.get("summary")
        participants_file = job_result_dict.get("participants_file")
        metrics = job_result_dict.get("metrics", {})
        sent_summary = False
        if summary:
            maxlen = 4096
            try:
                if len(summary) > maxlen:
                    logger.debug(f"Summary length {len(summary)} exceeds limit, splitting for user_id={user_id}")
                    await client.send_message(user_id, f"📋 Summary for chat {chat_id} (sending in multiple parts due to length)")
                    parts_sent = 0
                    for i in range(0, len(summary), maxlen):
                        part = summary[i:i+maxlen]
                        logger.debug(f"Sending summary part {parts_sent+1}: length={len(part)}")
                        await client.send_message(user_id, part)
                        parts_sent += 1
                        time.sleep(0.5)
                    logger.info(f"Split summary sent successfully: {parts_sent} parts")
                    sent_summary = True
                else:
                    logger.debug("Sending summary as single message")
                    await client.send_message(user_id, summary)
                    sent_summary = True
                    logger.info("Summary sent successfully")
            except Exception as e:
                logger.exception(f"[ERROR] Error sending summary message: {e}")
                try:
                    await client.send_message(user_id, f"❌ Error sending summary: {str(e)}\n\nThe summary was generated but could not be delivered.")
                except Exception as notify_error:
                    logger.error(f"[ERROR] Failed to send error notification: {notify_error}")
        if metrics and sent_summary:
            try:
                metrics_str = (
                    f"📊 Processing metrics:\n"
                    f"- Messages processed: {metrics.get('message_count', 'unknown')}\n"
                    f"- Extraction time: {metrics.get('extract_time_seconds', 'unknown')}s\n"
                    f"- LLM processing time: {metrics.get('llm_time_seconds', 'unknown')}s\n"
                    f"- Total processing time: {metrics.get('total_time_seconds', 'unknown')}s"
                )
                logger.debug("Sending metrics message")
                await client.send_message(user_id, metrics_str)
                logger.debug("Metrics message sent")
            except Exception as metrics_error:
                logger.error(f"[ERROR] Error sending metrics message: {metrics_error}")
        if participants_file and os.path.exists(participants_file):
            logger.info(f"Sending participants file: path={participants_file}")
            try:
                file_size = os.path.getsize(participants_file)
                logger.debug(f"Participants file size: {file_size} bytes")
                await client.send_file(user_id, participants_file, caption="📄 Chat participants list")
                logger.info("Participants file sent successfully")
            except Exception as file_error:
                logger.exception(f"[ERROR] Error sending participants file: {file_error}")
                try:
                    await client.send_message(user_id, f"❌ Error sending participants file: {str(file_error)}")
                except Exception as notify_error:
                    logger.error(f"[ERROR] Failed to send file error notification: {notify_error}")
            finally:
                try:
                    logger.debug(f"Cleaning up participants file: {participants_file}")
                    os.remove(participants_file)
                    logger.debug("File cleanup successful")
                except Exception as cleanup_error:
                    logger.error(f"[ERROR] Failed to clean up participants file: {cleanup_error}")
        logger.debug(f"[EXIT] send_llm_result OK")
    except Exception as e:
        logger.exception(f"[ERROR] Unhandled error in send_llm_result: {e}")
        try:
            error_traceback = traceback.format_exc()
            await client.send_message(user_id, f"❌ Internal error sending results: {str(e)}\n\nPlease contact support.")
        except Exception as final_error:
            logger.error(f"[ERROR] Failed to send error notification in exception handler: {final_error}")

async def send_failure_message(client: Any, user_id: int, chat_id: int, job_result_dict: Dict[str, Any]) -> None:
    """
    Sends failure message with details, logs all errors.
    """
    logger.debug(f"[ENTRY] send_failure_message(user_id={user_id}, chat_id={chat_id}, keys={list(job_result_dict.keys()) if isinstance(job_result_dict, dict) else type(job_result_dict)})")
    try:
        if not isinstance(job_result_dict, dict):
            logger.error(f"Invalid job result (not a dict): {type(job_result_dict)}")
            error = "Unknown error (invalid result format)"
            traceback_info = ""
        else:
            error = job_result_dict.get("error", "Unknown error")
            traceback_info = job_result_dict.get("traceback", "")
        logger.debug(f"Error details: {error}")
        failure_message = f"❌ Job failed for chat {chat_id}:\n\n{error}"
        if traceback_info and len(traceback_info) > 0:
            if len(traceback_info) > 3000:
                traceback_info = traceback_info[:3000] + "..."
            failure_message += f"\n\nDetails:\n```\n{traceback_info}\n```"
        logger.debug("Sending failure message to user")
        await client.send_message(user_id, failure_message)
        logger.info("Failure message sent successfully")
        logger.debug(f"[EXIT] send_failure_message OK")
    except Exception as e:
        logger.exception(f"[ERROR] Error sending failure message: {e}")
        try:
            await client.send_message(user_id, f"❌ Failed to process your request for chat {chat_id}. An internal error occurred.")
        except Exception as final_error:
            logger.error(f"[ERROR] Failed to send error notification in exception handler: {final_error}")
