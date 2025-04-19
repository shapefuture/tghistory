import logging
from app.userbot import state
from typing import Optional
import traceback

logger = logging.getLogger("userbot.ui")

async def update_status_message_for_request(client, request_id):
    """
    Update status message in Telegram with current job status
    
    Args:
        client: Telethon client instance
        request_id: Request ID to update status for
    """
    logger.debug(f"Updating status message for request: {request_id}")
    
    try:
        # Get request data
        logger.debug(f"Retrieving request data: request_id={request_id}")
        request_data = state.get_request_data(request_id)
        
        if not request_data:
            logger.warning(f"No request data found for request_id={request_id}")
            return
            
        # Extract data
        user_id = request_data.get("user_id")
        chat_id = request_data.get("target_chat_id")
        status = request_data.get("status")
        
        if not user_id or not chat_id or not status:
            logger.warning(f"Missing required fields in request data: user_id={user_id}, chat_id={chat_id}, status={status}")
            return
            
        logger.debug(f"Request data: user_id={user_id}, chat_id={chat_id}, status={status}")
        
        # Get status message ID
        logger.debug(f"Retrieving status message ID: user_id={user_id}, chat_id={chat_id}")
        msg_id = state.get_status_message(user_id, chat_id)
        
        if not msg_id:
            logger.warning(f"No status message found for user_id={user_id}, chat_id={chat_id}")
            return
            
        logger.debug(f"Found status message: msg_id={msg_id}")

        # Format status message
        status_icons = {
            "PENDING_PROMPT": "✏️",
            "QUEUED": "⏳",
            "STARTED": "🔄",
            "EXTRACTING_HISTORY": "📃",
            "PROGRESS": "📊",
            "EXTRACTING_PARTICIPANTS": "👥",
            "WAITING": "⏱️",
            "CALLING_LLM": "🧠",
            "SUCCESS": "✅",
            "FAILED": "❌"
        }
        
        icon = status_icons.get(status, "🔄")
        
        # Add details based on status
        detail = ""
        if status == "PROGRESS":
            count = request_data.get("progress", "unknown")
            detail = f" ({count} messages processed)"
        elif status == "WAITING":
            detail = " (rate limit, please wait)"
        
        txt = f"{icon} Status for chat {chat_id}: {status}{detail}"
        logger.debug(f"Status message text: {txt}")

        # Edit message
        try:
            logger.debug(f"Editing message: user_id={user_id}, msg_id={msg_id}")
            await client.edit_message(user_id, int(msg_id), txt)
            logger.info(f"Status message updated successfully: request_id={request_id}, status={status}")
        except Exception as edit_error:
            logger.warning(f"Failed to edit status message: {edit_error}")
            
            # Try to determine if this is a "message not modified" error (which is normal and can be ignored)
            error_str = str(edit_error).lower()
            if "not modified" in error_str or "message is not modified" in error_str:
                logger.debug("Ignoring 'message not modified' error")
            else:
                # Log the full error for other cases
                logger.error(f"Error editing message: {edit_error}")
    except Exception as e:
        logger.exception(f"Unexpected error updating status message for request_id={request_id}: {e}")