from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from app.crud import get_processing_request
from app.schemas import ProcessingRequestSchema
from app import config
import os

router = APIRouter()

def fake_current_user():
    # Placeholder for auth
    return "user_id"

@router.get("/api/status/{request_id}", response_model=ProcessingRequestSchema)
def api_status(request_id: str, user = Depends(fake_current_user)):
    req = get_processing_request(request_id)
    if not req or req.user_id != user:
        raise HTTPException(status_code=404)
    return req

@router.get("/status/{request_id}")
def status_page(request_id: str, user = Depends(fake_current_user)):
    # Render template: just stub here
    req = get_processing_request(request_id)
    if not req or req.user_id != user:
        raise HTTPException(status_code=404)
    return {"request": req}

@router.get("/download/{task_id}/{filename}")
def download_file(task_id: str, filename: str, user=Depends(fake_current_user)):
    # Find processing request by task_id (for MVP, just task_id == request_id)
    req = get_processing_request(task_id)
    if not req or req.user_id != user or not req.tasks or not req.tasks[0].participants_file:
        raise HTTPException(status_code=404)
    fullpath = req.tasks[0].participants_file
    if os.path.basename(fullpath) != filename or not os.path.exists(fullpath):
        raise HTTPException(status_code=404)
    return FileResponse(fullpath, filename=filename)