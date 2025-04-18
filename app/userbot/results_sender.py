import os
import logging

logger = logging.getLogger("userbot.results_sender")

async def send_llm_result(client, user_id, chat_id, job_result_dict):
    summary = job_result_dict.get("summary")
    participants_file = job_result_dict.get("participants_file")
    # Send summary (break up long messages)
    if summary:
        maxlen = 4096
        if len(summary) > maxlen:
            for i in range(0, len(summary), maxlen):
                await client.send_message(user_id, summary[i:i+maxlen])
        else:
            await client.send_message(user_id, summary)
    # Send participant file if exists
    if participants_file and os.path.exists(participants_file):
        try:
            await client.send_file(user_id, participants_file, caption="📄 Chat participants")
        finally:
            try: os.remove(participants_file)
            except Exception: pass

async def send_failure_message(client, user_id, chat_id, job_result_dict):
    error = job_result_dict.get("error", "Unknown error")
    await client.send_message(user_id, f"❌ Job failed for chat {chat_id}: {error}")