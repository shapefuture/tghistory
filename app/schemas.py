from typing import Optional
from pydantic import BaseModel

class TaskStatusSchema(BaseModel):
    chat_id: str
    status: str
    detail: Optional[str] = None
    progress: Optional[int] = None
    participants_file: Optional[str] = None
    summary: Optional[str] = None
    error: Optional[str] = None

class ProcessingRequestSchema(BaseModel):
    request_id: str
    user_id: str
    tasks: list[TaskStatusSchema]