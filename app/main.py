import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from typing import Callable

from app.shared.metrics import MetricsCollector
from app.routers import monitoring, processing

logger = logging.getLogger("api")

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="app/templates")

@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable):
    start_time = time.time()
    logger.info(f"API request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        endpoint = request.url.path
        status_code = response.status_code
        if not endpoint.startswith('/health'):
            MetricsCollector.record_api_metrics(endpoint, process_time, status_code)
        logger.info(f"API response: {endpoint} status={status_code} time={process_time:.3f}s")
        return response
    except Exception as e:
        logger.error(f"API middleware error: {e}", exc_info=True)
        raise

app.include_router(monitoring.router)
app.include_router(processing.router)

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    try:
        return {
            "name": "Telegram Extractor API",
            "version": "1.0.0",
            "status": "online",
            "docs_url": "/docs"
        }
    except Exception as e:
        logger.error(f"Root endpoint error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
