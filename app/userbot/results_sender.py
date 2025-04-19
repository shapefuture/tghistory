import os
import logging
import traceback
from typing import Dict, Any, Optional
import time

logger = logging.getLogger("userbot.results_sender")

async def send_llm_result(client, user_id, chat_id, job_result_dict):
    """
    Send LLM results to the user via Telegram
    
    Args:
        client: Telethon client instance
        user_id: Telegram user ID to send results to
        chat_id: Target chat ID that was processed
        job_result_dict: Dictionary containing job results
    """
    logger.info(f"Sending LLM result: user_id={user_id}, chat_id={chat_id}")
    
    try:
        # Extract data from job result
        if not isinstance(job_result_dict, dict):
            logger.error(f"Invalid job result (not a dict): {type(job_result_dict)}")
            await client.send_message(user_id, f"❌ Invalid job result format. Please contact support.")
            return
            
        summary = job_result_dict.get("summary")
        participants_file = job_result_dict.get("participants_file")
        metrics = job_result_dict.get("metrics", {})
        
        logger.debug(f"Extracted result data: summary_length={len(summary) if summary else 0}, has_participants_file={participants_file is not None}")
        
        # Send summary (break up long messages)
        sent_summary = False
        if summary:
            maxlen = 4096  # Telegram message size limit
            
            try:
                if len(summary) > maxlen:
                    logger.debug(f"Summary exceeds Telegram limit, splitting into chunks: length={len(summary)}")
                    
                    # Send intro message
                    await client.send_message(user_id, f"📋 Summary for chat {chat_id} (sending in multiple parts due to length)")
                    
                    # Split and send parts
                    parts_sent = 0
                    for i in range(0, len(summary), maxlen):
                        part = summary[i:i+maxlen]
                        logger.debug(f"Sending summary part {parts_sent+1}: length={len(part)}")
                        
                        await client.send_message(user_id, part)
                        parts_sent += 1
                        
                        # Small delay to prevent rate limiting
                        time.sleep(0.5)
                        
                    logger.info(f"Split summary sent successfully: {parts_sent} parts")
                    sent_summary = True
                else:
                    logger.debug("Sending summary as single message")
                    await client.send_message(user_id, summary)
                    sent_summary = True
                    logger.info("Summary sent successfully")
            except Exception as e:
                logger.exception(f"Error sending summary message: {e}")
                try:
                    await client.send_message(
                        user_id, 
                        f"❌ Error sending summary: {str(e)}\n\nThe summary was generated but could not be delivered."
                    )
                except Exception as notify_error:
                    logger.error(f"Failed to send error notification: {notify_error}")
        
        # Send metrics if available
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
                logger.error(f"Error sending metrics message: {metrics_error}")
        
        # Send participant file if exists
        if participants_file and os.path.exists(participants_file):
            logger.info(f"Sending participants file: path={participants_file}")
            try:
                # Get file size for logging
                file_size = os.path.getsize(participants_file)
                logger.debug(f"Participants file size: {file_size} bytes")
                
                # Send file
                await client.send_file(
                    user_id, 
                    participants_file, 
                    caption="📄 Chat participants list"
                )
                logger.info("Participants file sent successfully")
            except Exception as file_error:
                logger.exception(f"Error sending participants file: {file_error}")
                try:
                    await client.send_message(
                        user_id,
                        f"❌ Error sending participants file: {str(file_error)}"
                    )
                except Exception as notify_error:
                    logger.error(f"Failed to send file error notification: {notify_error}")
            finally:
                # Clean up the file
                try:
                    logger.debug(f"Cleaning up participants file: {participants_file}")
                    os.remove(participants_file)
                    logger.debug("File cleanup successful")
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up participants file: {cleanup_error}")
    except Exception as e:
        logger.exception(f"Unhandled error in send_llm_result: {e}")
        try:
            error_traceback = traceback.format_exc()
            await client.send_message(
                user_id,
                f"❌ Internal error sending results: {str(e)}\n\nPlease contact support."
            )
        except Exception as final_error:
            logger.error(f"Failed to send error notification in exception handler: {final_error}")

async def send_failure_message(client, user_id, chat_id, job_result_dict):
    """
    Send job failure notification to the user
    
    Args:
        client: Telethon client instance
        user_id: Telegram user ID to send message to
        chat_id: Target chat ID that was processed
        job_result_dict: Dictionary containing error information
    """
    logger.info(f"Sending failure message: user_id={user_id}, chat_id={chat_id}")
    
    try:
        # Extract error information
        if not isinstance(job_result_dict, dict):
            logger.error(f"Invalid job result (not a dict): {type(job_result_dict)}")
            error = "Unknown error (invalid result format)"
        else:
            error = job_result_dict.get("error", "Unknown error")
            traceback_info = job_result_dict.get("traceback", "")
            
        logger.debug(f"Error details: {error}")
        
        # Prepare and send message
        failure_message = f"❌ Job failed for chat {chat_id}:\n\n{error}"
        
        # Add detailed error for debugging if available
        if traceback_info and len(traceback_info) > 0:
            # Keep traceback info short enough for Telegram
            if len(traceback_info) > 3000:
                traceback_info = traceback_info[:3000] + "..."
                
            failure_message += f"\n\nDetails:\n```\n{traceback_info}\n```"
            
        logger.debug("Sending failure message to user")
        await client.send_message(user_id, failure_message)
        logger.info("Failure message sent successfully")
    except Exception as e:
        logger.exception(f"Error sending failure message: {e}")
        try:
            await client.send_message(
                user_id,
                f"❌ Failed to process your request for chat {chat_id}. An internal error occurred."
            )
        except Exception as final_error:
            logger.error(f"Failed to send error notification in exception handler: {final_error}")