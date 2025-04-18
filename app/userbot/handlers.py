import logging
import random
import string
from telethon.events import NewMessage
from telethon.tl.types import Message
from app.userbot import state
from app.shared.redis_client import get_rq_queue
from app import config

logger = logging.getLogger("userbot.handlers")

def _gen_request_id(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def register_handlers(client):
    @client.on(NewMessage(outgoing=False, from_users='me'))
    async def handle_message_input(event: Message):
        user_id = event.sender_id
        text = event.raw_text.strip() if hasattr(event, "raw_text") else ""
        request_id = state.get_pending_state(user_id)

        # Handle prompt input if pending
        if request_id:
            if text.lower() == '/cancel':
                state.clear_pending_state(user_id)
                await event.respond("❌ Operation cancelled.")
                return

            if not text or len(text) < 3:
                await event.respond("⚠️ Please provide a valid prompt (min 3 chars) or /cancel.")
                return

            # Store prompt, update state, clear pending, enqueue
            state.store_request_data(request_id, {"custom_prompt": text, "status": "QUEUED"})
            state.clear_pending_state(user_id)
            await enqueue_processing_job(event, user_id, request_id, custom_prompt=text)
            msg = await event.respond("✅ Prompt received! The job is being queued.")
            state.set_status_message(user_id, event.chat_id, msg.id)
            return

        # Not pending: specify target chat
        if event.is_group or event.is_channel or event.fwd_from:
            try:
                if hasattr(event, "forward"):
                    entity = await event.get_forwarded_from()
                else:
                    entity = await event.get_chat()
                chat_id = getattr(entity, "id", None) or event.chat_id
            except Exception as e:
                logger.warning(f"Target chat parse fail: {e}")
                await event.respond("❌ Could not detect chat. Forward a message or name the chat/channel.")
                return
        elif text:
            # Try resolve username or ID
            try:
                entity = await client.get_entity(text)
                chat_id = entity.id
            except Exception:
                await event.respond("❌ Invalid chat username/ID. Try again, or forward a message.")
                return
        else:
            await event.respond("❌ Please forward a message or type a chat/channel username/ID.")
            return

        # Ready: generate request_id, store state, prompt user for LLM prompt
        req_id = _gen_request_id()
        state.store_request_data(req_id, {
            "target_chat_id": chat_id,
            "status": "PENDING_PROMPT",
            "user_id": user_id,
        })
        state.set_pending_prompt_state(user_id, req_id)
        await event.respond("✏️ Now send me your summarization prompt for this chat (or /cancel).")

async def enqueue_processing_job(event, user_id, request_id, custom_prompt):
    queue = get_rq_queue(get_rq_queue.__globals__["get_redis_connection"](config.settings), config.settings)
    request_data = state.get_request_data(request_id)
    chat_id = request_data.get("target_chat_id")
    session_path = config.settings.TELEGRAM_SESSION_PATH

    # Enqueue job, update status, store rq_job_id
    state.update_request_status(request_id, "QUEUED")
    job = queue.enqueue(
        "app.worker.tasks.extract_and_summarize_data",
        chat_id,
        session_path,
        user_id,
        request_id,
        custom_prompt,
        job_id=f"extract:{request_id}:{chat_id}",
        meta={'chat_id': chat_id, 'user_id': user_id, 'request_id': request_id}
    )
    state.add_rq_job_id(request_id, job.id)
    logger.info(f"Enqueued job: {job.id} for user {user_id} chat {chat_id}")