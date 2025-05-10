import logging
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends, Response, Header
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.crud import get_processing_request, get_task_status
from app.schemas import ProcessingRequestSchema
from app import config

logger = logging.getLogger("api.processing")
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_current_user(x_user_id: Optional[str] = Header(None)) -> int:
    """
    Validate and return the current user ID from X-User-Id header.
    Raises HTTPException if not present or invalid.
    """
    logger.debug(f"get_current_user: X-User-Id header={x_user_id}")
    if not x_user_id:
        logger.warning("Missing X-User-Id header")
        raise HTTPException(status_code=401, detail="Missing X-User-Id header (user authentication required)")
    try:
        user_id = int(x_user_id)
        logger.debug(f"Authenticated user_id: {user_id}")
        return user_id
    except Exception as e:
        logger.error(f"Invalid X-User-Id header value: {x_user_id} ({e})")
        raise HTTPException(status_code=401, detail="Invalid X-User-Id header (must be integer)")

def check_request_ownership(request_obj: ProcessingRequestSchema, user_id: int):
    logger.debug(f"check_request_ownership: checking request.user_id={request_obj.user_id} vs auth user_id={user_id}")
    if int(request_obj.user_id) != int(user_id):
        logger.warning(f"User {user_id} not authorized for request owned by {request_obj.user_id}")
        raise HTTPException(status_code=403, detail="You are not authorized to access this request")

@router.get("/status/{request_id}", response_class=HTMLResponse)
async def status_page(request_id: str, request: Request, user_id: int = Depends(get_current_user)):
    logger.info(f"Status page requested: request_id={request_id}, user_id={user_id}")
    try:
        req = get_processing_request(request_id)
        if not req:
            logger.warning(f"Status page not found: request_id={request_id}")
            return HTMLResponse(content=f"Request not found: {request_id}", status_code=404)
        check_request_ownership(req, user_id)
        logger.debug(f"Rendering status page for request_id={request_id}")
        return templates.TemplateResponse("main/status.html", {"request": request, "req": req})
    except HTTPException as he:
        logger.error(f"Status page HTTPException: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Error in status_page: {e}", exc_info=True)
        return HTMLResponse(content=f"Internal server error: {e}", status_code=500)

@router.get("/api/status/{request_id}")
async def api_status(request_id: str, user_id: int = Depends(get_current_user)):
    logger.info(f"API status requested: request_id={request_id}, user_id={user_id}")
    try:
        status = get_task_status(request_id)
        if not status:
            logger.warning(f"API status not found: request_id={request_id}")
            raise HTTPException(status_code=404, detail="Request not found")
        req = get_processing_request(request_id)
        if not req:
            logger.warning(f"Processing request not found for status check: request_id={request_id}")
            raise HTTPException(status_code=404, detail="Request not found")
        check_request_ownership(req, user_id)
        logger.debug(f"Returning API status for request_id={request_id}")
        return status.dict()
    except HTTPException as he:
        logger.error(f"API status HTTPException: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Error in api_status: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/download/{task_id}/{filename}")
async def download_file(task_id: str, filename: str, user_id: int = Depends(get_current_user)):
    logger.info(f"Download file requested: task_id={task_id}, filename={filename}, user_id={user_id}")
    try:
        req = get_processing_request(task_id)
        if not req:
            logger.warning(f"Download request not found: task_id={task_id}")
            raise HTTPException(status_code=404, detail="Request not found")
        check_request_ownership(req, user_id)
        file_path = os.path.join(config.settings.OUTPUT_DIR_PATH, filename)
        if not os.path.isfile(file_path):
            logger.warning(f"File not found: {file_path}")
            raise HTTPException(status_code=404, detail="File not found")
        logger.info(f"Serving file: {file_path}")
        return FileResponse(file_path, media_type="application/octet-stream", filename=filename)
    except HTTPException as he:
        logger.error(f"Download file HTTPException: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Download file error: {e}", exc_info=True)
        return Response(content=f"Internal server error: {e}", status_code=500)
