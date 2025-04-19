from typing import Optional
from app.schemas import ProcessingRequestSchema, TaskStatusSchema

# These would typically be DB accessors; here we'll adapt for Redis for MVP

from app.shared.redis_client import get_redis_connection
from app import config

def get_processing_request(request_id: str) -> Optional[ProcessingRequestSchema]:
    r = get_redis_connection(config.settings)
    req = r.hgetall(f"request:{request_id}:data")
    if not req:
        return None
    user_id = req.get(b"user_id", b"").decode()
    chat_id = req.get(b"target_chat_id", b"").decode()
    status = req.get(b"status", b"").decode()
    participants_file = req.get(b"participants_file", b"").decode() if req.get(b"participants_file") else None
    summary = req.get(b"summary", b"").decode() if req.get(b"summary") else None
    error = req.get(b"error", b"").decode() if req.get(b"error") else None
    tasks = [
        TaskStatusSchema(
            chat_id=chat_id,
            status=status,
            detail=None,
            progress=None,
            participants_file=participants_file,
            summary=summary,
            error=error
        )
    ]
    return ProcessingRequestSchema(request_id=request_id, user_id=user_id, tasks=tasks)