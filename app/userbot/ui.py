import logging
from app.userbot import state

logger = logging.getLogger("userbot.ui")

async def update_status_message_for_request(client, request_id):
    request_data = state.get_request_data(request_id)
    if not request_data:
        logger.warning(f"No request data for {request_id}")
        return
    user_id = request_data["user_id"]
    chat_id = request_data["target_chat_id"]
    status = request_data["status"]
    msg_id = state.get_status_message(user_id, chat_id)
    if not msg_id:
        return

    txt = f"🔄 Status for chat {chat_id}: {status}"
    try:
        await client.edit_message(user_id, int(msg_id), txt)
    except Exception as e:
        logger.warning(f"Failed to edit status message: {e}")