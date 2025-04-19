from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import FileResponse
from app.crud import get_processing_request
from app.schemas import ProcessingRequestSchema
from app import config
import os
import logging
import hashlib
import time

router = APIRouter()
logger = logging.getLogger("api.processing")

# Security warning for developers
"""
SECURITY WARNING: This authentication is placeholder only!
Before production deployment, implement proper authentication.
Options include:
1. OAuth2 with JWT
2. API keys with proper validation
3. Session-based auth with secure cookie handling

The current implementation is NOT SECURE and is for development only.
"""

async def get_current_user(request: Request):
    """
    PLACEHOLDER AUTH - REPLACE BEFORE PRODUCTION
    
    This is NOT a secure authentication system.
    It's included as a clear placeholder that needs replacement.
    """
    # In production, implement proper security here
    
    # Log security warning on each auth attempt
    logger.warning("SECURITY: Using placeholder authentication - MUST be replaced before production")
    
    # For now, return a placeholder user ID
    return "placeholder_user_id"

@router.get("/api/status/{request_id}", response_model=ProcessingRequestSchema)
def api_status(request_id: str, user = Depends(get_current_user)):
    req = get_processing_request(request_id)
    if not req or req.user_id != user:
        raise HTTPException(status_code=404)
    return req

@router.get("/status/{request_id}")
def status_page(request_id: str, user = Depends(get_current_user)):
    # Render template: just stub here
    req = get_processing_request(request_id)
    if not req or req.user_id != user:
        raise HTTPException(status_code=404)
    return {"request": req}

@router.get("/download/{task_id}/{filename}")
def download_file(task_id: str, filename: str, user=Depends(get_current_user)):
    # Find processing request by task_id (for MVP, just task_id == request_id)
    req = get_processing_request(task_id)
    if not req or req.user_id != user or not req.tasks or not req.tasks[0].participants_file:
        raise HTTPException(status_code=404)
    fullpath = req.tasks[0].participants_file
    if os.path.basename(fullpath) != filename or not os.path.exists(fullpath):
        raise HTTPException(status_code=404)
    return FileResponse(fullpath, filename=filename)