"""
Main FastAPI application entry point.

Sets up the FastAPI application with all routes and middleware.
"""
import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from app.logging_config import setup_logging
from app.routers import processing, monitoring
from app.shared.metrics import MetricsCollector

logger = logging.getLogger("api")

# Initialize logging
setup_logging(config.settings)

# Create FastAPI app
app = FastAPI(
    title="Telegram Extractor API",
    description="API for Telegram chat extraction and summarization",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Record API metrics
    # Extract endpoint path, removing query parameters
    endpoint = request.url.path
    status_code = response.status_code
    
    # Don't record metrics for health checks to avoid bloating metrics
    if not endpoint.startswith('/health'):
        MetricsCollector.record_api_metrics(endpoint, process_time, status_code)
    
    return response

# Include routers
app.include_router(processing.router, prefix="/api")
app.include_router(monitoring.router)

# Root route
@app.get("/")
async def root():
    """Root endpoint that returns basic API info"""
    return {
        "name": "Telegram Extractor API",
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    # Start the FastAPI server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_config=None  # Use our custom logging config
    )