# ... (imports unchanged) ...
logger = logging.getLogger("api")

# ... (logging/cors/templates setup unchanged) ...

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

# ... (router includes unchanged) ...

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

# ... (uvicorn-run block unchanged) ...
