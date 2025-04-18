import logging
import json
from typing import Optional

from app.shared.redis_client import get_redis_connection
from app.worker.llm_service import get_llm_summary
from app.worker.utils import clean_message_text
from app import config

from telethon.sync import TelegramClient
from telethon.errors.rpcerrorlist import FloodWaitError

logger = logging.getLogger("worker.tasks")

def extract_and_summarize_data(chat_id, user_session_path, user_id, request_id, custom_prompt):
    job = None
    redis_conn = get_redis_connection(config.settings)

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
        publish_status('STARTED')

        # Connect Telethon session
        client = TelegramClient(user_session_path, config.settings.TELEGRAM_API_ID, config.settings.TELEGRAM_API_HASH)
        client.connect()
        if not client.is_user_authorized():
            publish_status('FAILED', detail="User not authorized.")
            return {"status": "FAILURE", "error": "User not authorized."}

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
        except FloodWaitError as fw:
            import time
            logger.warning(f"FloodWait: Sleeping {fw.seconds}s")
            publish_status('WAITING', detail=f"Flood wait: {fw.seconds}s")
            time.sleep(fw.seconds)

        history_text = "\n".join(history)
        participants_text = None

        # (Optional) Group participant extraction
        entity = client.get_entity(chat_id)
        if hasattr(entity, "participants_count") and entity.participants_count:
            try:
                publish_status('EXTRACTING_PARTICIPANTS')
                parts = []
                for user in client.get_participants(chat_id):
                    parts.append(f"{user.id}\t{user.first_name} {user.last_name or ''} @{user.username or ''}".strip())
                participants_text = "\n".join(parts)
            except Exception as e:
                logger.error(f"Participant extraction error: {e}")

        client.disconnect()

        if not history_text:
            raise ValueError("No text history extracted.")

        publish_status('CALLING_LLM')
        import asyncio
        summary = asyncio.run(get_llm_summary(custom_prompt, history_text, config.settings))
        if not summary:
            raise RuntimeError("LLM summarization failed.")

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
        publish_status('SUCCESS')
        return {
            "status": "SUCCESS",
            "summary": summary,
            "participants_file": participants_file,
            "request_id": request_id,
            "user_id": user_id,
            "chat_id": chat_id,
        }
    except Exception as e:
        logger.exception(f"Task error: {e}")
        error_message = f"{type(e).__name__}: {str(e)}"
        publish_status('FAILED', detail=error_message)
        return {"status": "FAILURE", "error": error_message}