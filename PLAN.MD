Okay, let's perform a critical analysis of the implementation_plan.md (v4.1 - Userbot + RQ + LLM) to identify ambiguities, missing guidance, and areas for improvement, then refine it into the ultimate, hyper-detailed plan for AI execution, infused with best practices.

Analysis of Plan v4.1:

Strengths:

Clear architecture (Userbot Frontend + RQ/Redis Backend).

Logical phasing.

Addresses core functionality (Auth, Input, Extraction, LLM Call, Results).

Includes key technologies (Telethon, RQ, Redis, httpx).

Mentions essential concepts (State via Redis, Background Tasks, Config, Logging, Testing).

Good separation of concerns in the proposed structure.

Ambiguities & Missing Guidance:

Initial Authentication: While mentioning Render Shell for the first auth, it lacks explicit steps or error handling guidance within the script if the session file is missing or invalid on subsequent starts. The userbot must be able to guide the developer running it via logs if auth fails.

State Management Details: "Store state in Redis" is mentioned, but the exact keys, data structures (Hashes vs Sets vs Strings), and TTLs need precise definition for clarity, especially for managing the conversation state (waiting for prompt) and tracking multiple concurrent job requests per user (though initially single-user).

Error Handling Specificity: Needs more detail on which specific Telethon/RQ/Redis/httpx exceptions to catch in each block and how to translate them into user-facing status updates or specific return values/logged messages. How are network timeouts handled vs. API errors vs. permission errors?

Progress Updates: Plan mentions "periodically call update_tg_status" or "poll meta", but the mechanism isn't fully detailed. Direct editing from the worker is complex due to needing the client instance. Polling job meta requires the userbot to actively poll all running jobs, which could be inefficient if many jobs run. A Redis Pub/Sub mechanism, while more setup, is often better for real-time updates but needs explicit definition. Decision needed: Which progress update mechanism and how is it implemented?

LLM Token Limits: Doesn't explicitly address how to handle chat histories exceeding the LLM's context window limit (truncation strategy needed).

Concurrency Handling (Userbot): If the user sends multiple requests quickly, how does the userbot handle overlapping state checks or conversation attempts? (Less critical for single-user 'me' bot, but worth noting).

File Cleanup (Precise): Needs explicit steps on when and how temporary files (like the participant list before upload) are reliably deleted, even if errors occur during upload.

Configuration Validation: config.py needs stronger emphasis on validating loaded values (e.g., are API keys present? Is Redis URL valid?).

Testing Strategy Details: Needs more explicit guidance on what to mock (e.g., "mock telethon.TelegramClient.connect to return successfully", "mock redis.Redis.hset", "mock httpx.AsyncClient.post to return specific status codes or raise exceptions").

Deployment (render.yaml): Needs specific examples of environment variable mapping (especially secrets and service URLs like Redis) and persistent disk configuration syntax.

Idempotency: Are RQ tasks safe to retry if they fail mid-way (e.g., after partially writing a file)? (Likely not fully idempotent, relying on unique filenames helps mitigate overwrites).

Security: While mentioned, specifics like rate limiting internal API calls (if any added later), input sanitization beyond basic checks, and secure handling of the session file path need reinforcement.

Revising for Ultimate Clarity and Best Practices:

We will:

Define Redis keys/structures explicitly.

Choose and detail Redis Pub/Sub for progress/completion notifications (more robust than polling/direct edit).

Add LLM truncation logic.

Specify exception handling more granularly.

Detail file cleanup using try...finally.

Emphasize config validation.

Provide more concrete testing instructions.

Add detail to render.yaml requirements.

Integrate best practices directly into steps.

implementation_plan.md (v5.0 - Ultimate AI Guide)

# Project: Cloud-Hosted Telegram Extractor & Summarizer Userbot (v5.0)

**Goal:** Develop a secure, robust, scalable, and user-friendly userbot hosted on Render.com. The bot, interacting via Telegram, allows the user (the owner) to specify a chat/channel (via username, link, or forward), provide a custom prompt, triggers background extraction and LLM summarization (via NotebookLM/Gemini/OpenRouter), provides real-time progress updates via Redis Pub/Sub and message edits, and delivers the summary/results back within Telegram.

**Architecture:** Interactive Telethon Userbot (Frontend/Controller) + RQ/Redis Queue + RQ Workers (Backend Extraction & LLM Call) + Redis Pub/Sub (Progress/Completion Events) + Persistent Storage (Session & Output Files).

**Target Platform:** Render.com

**Guiding Principles:** User Experience First (Telegram Native, Responsive), AI Development Ease (Hyper-Modular, Explicit Steps, Standard Patterns), Robustness & Scalability (Decoupled, Queued, Persistent State), Security (Secrets, Session, File Handling), Maintainability & Testability (Clean Code, Typed, Logged, Tested).

**Technology Stack:**
*   **Core:** Python 3.9+
*   **Telegram Interaction:** Telethon
*   **Task Queue:** RQ
*   **Broker/State/PubSub:** Redis (Render Managed Service)
*   **LLM Interaction:** `httpx`
*   **Configuration:** Pydantic `BaseSettings` via `config.py` from Env Vars.
*   **Logging:** Python `logging` module + Structlog (Recommended).
*   **Testing:** `pytest`, `pytest-asyncio`, `pytest-mock`, `fakeredis[lua]`.
*   **Linting/Formatting:** `black`, `flake8`, `mypy`.
*   **Deployment:** Git repository + `render.yaml`.

**Project Structure:** (Same as v4.1)

---
**AI Implementation Best Practices Checklist (MANDATORY for each step):**
*   **(All previous best practices apply - Style, Typing, Modularity, Config, Security, Error Handling, Logging, Testing, Docs, Dependencies)**
*   **[ ] Idempotency:** Design tasks to be as safe as possible for retries. Use unique filenames including job/request IDs to prevent overwrites.
*   **[ ] Resource Management:** Explicitly use `try...finally` or context managers (`async with`) for file handles, network connections (Telethon client, httpx client), ensuring cleanup/disconnection even if errors occur.
*   **[ ] State Design:** Use clear, documented Redis keys and appropriate data structures (Hashes for job details, Sets for selections/active requests, Pub/Sub channels for events). Define TTLs where appropriate.
*   **[ ] Async Correctness:** Ensure `await` is used for all coroutines (Telethon, httpx, async Redis calls if used). Avoid blocking calls in async functions. Use `asyncio.create_task` correctly for background loops.
*   **[ ] Explicit Instructions:** Break down prompts into single file/function/method implementations. Provide full context (imports, function signatures, required variables). Specify exact library methods and expected error handling. **State explicitly: "This is a Telethon Userbot, do NOT use Bot API methods like Web Apps or Webhooks unless specified for communication."**

---

## Phase 1: Foundation, Config, Deployment Setup (Enhanced Validation)

**Goal:** Set up project structure, environment, robust configuration loading/validation, logging, Redis connection helper, basic Telethon client setup, empty RQ task file, and the initial `render.yaml`.

**Steps:**

1.  `[v]` Project Setup: Create structure. Init Git. Setup `venv`.
2.  `[ ]` Dependencies (`requirements.txt`): Define core + test/lint. `pip install -r requirements.txt`. Add `pydantic[dotenv]` for config. Add `structlog` (optional).
3.  **[ ] Configuration (`app/config.py`, `.env`):**
    *   `[ ]` Implement Pydantic `BaseSettings` class `Settings`. Load *all* configs (`TELEGRAM_API_ID: int`, `TELEGRAM_API_HASH: str`, `TELEGRAM_SESSION_PATH: str`, `REDIS_URL: str`, `OUTPUT_DIR_PATH: str`, `LOG_LEVEL: str`, `RQ_QUEUE_NAME: str` = 'default', `LLM_API_KEY: str`, `LLM_ENDPOINT_URL: Optional[str]`, `LLM_MODEL_NAME: Optional[str]`, `MAX_LLM_HISTORY_TOKENS: int` = 3000).
    *   `[ ]` Add validators (`@validator(...)`) for critical fields (e.g., check API ID/Hash format, check paths exist/are writable locally if needed, parse `REDIS_URL`). Log validation errors and exit gracefully if critical configs missing.
    *   `[ ]` Instantiate `settings = Settings()` globally in `config.py` for easy import.
    *   `[ ]` Create `.env` for local secrets/overrides. Update `.gitignore`.
4.  **[ ] Logging Setup (`app/logging_config.py`):** Implement `setup_logging(settings: config.Settings)` using config level. Configure `structlog` if using.
5.  **[ ] Redis Client & Queue (`app/shared/redis_client.py`):**
    *   `[ ]` Implement `get_redis_connection(settings: config.Settings)` -> `redis.Redis`: Parses `settings.REDIS_URL`, creates instance, pings, caches connection. Raises specific exception on connection failure.
    *   `[ ]` Implement `get_rq_queue(redis_conn: redis.Redis, settings: config.Settings)` -> `rq.Queue`: Returns `Queue(settings.RQ_QUEUE_NAME, connection=redis_conn)`.
6.  **[ ] Telethon Client Helper (`app/userbot/client.py`):** Implement `get_telethon_client(settings: config.Settings)` returning unconnected client.
7.  **[ ] Empty Task (`app/worker/tasks.py`):** Create file. Define `def extract_and_summarize_data(...): raise NotImplementedError`.
8.  **[ ] Worker Entry Point (`worker/run_worker.py`):** Import necessary modules. Call `setup_logging`. Get Redis connection, start `rq.Worker`. Include top-level `try...except` for startup errors.
9.  **[ ] Userbot Entry Point (`run_userbot.py`):** Import necessary modules. Call `setup_logging`. Get client. Implement `async def main():` loop with `client.start()` (see step 10) and `client.run_until_disconnected()`.
10. **[ ] Initial Authentication Handling (`run_userbot.py` - `main`):**
    *   `[ ]` Wrap `await client.start()` in `try...except`.
    *   `[ ]` Catch `Exception` during startup. Log detailed error.
    *   `[ ]` Add specific check: `if not await client.is_user_authorized(): logger.critical("User is NOT authorized. Session file might be invalid or missing. Please run interactively once via Render Shell or locally to authenticate.")` (Maybe exit here or loop trying to connect?) **Decision:** Exit after logging critical error, as it requires manual intervention.
11. **[ ] `render.yaml`:** Define `redis`, `userbot` worker, `rqworker` worker, persistent disk (`/data`), map **all** required environment variables from Render Secrets, set start commands, mount disk correctly. Ensure Redis URL env var uses Render's internal service address.
12. **[ ] Initial Tests:** Unit test `config.py` validation, `redis_client.py` (fakeredis), `client.py`.
13. **[ ] Manual/Deployment Test:** Deploy. Check logs for validation errors. Use Render Shell for *initial* `run_userbot.py` auth. Verify session file created on `/data`. Verify both services start, connect to Redis, userbot logs successful connection.

**End of Phase 1:** Robust foundation with validated config, persistent session handling established, ready for deployment structure verification.

---

## Phase 2: Userbot - Input Handling & Prompt Conversation (via Redis State)

**Goal:** Implement Telethon handlers for chat specification (text/forward) and the subsequent prompt request, managing the conversational state using Redis Hashes.

**Steps:**

1.  **[ ] State Management (`app/userbot/state.py`):**
    *   `[ ]` Define Redis keys clearly (e.g., `f"user:{user_id}:state"`, `f"request:{request_id}:data"`).
    *   `[ ]` Use Redis Hashes:
        *   `user:{user_id}:state` (Hash): `field='pending_request_id', value='req_xyz'` or `field='status_message:{chat_id}', value=message_id`. Use TTLs for pending states (e.g., 5 minutes).
        *   `request:{request_id}:data` (Hash): `field='status', value='PENDING_PROMPT'/'QUEUED'/'RUNNING'/'DONE'`, `field='target_chat_id', value=...`, `field='custom_prompt', value=...`, `field='user_id', value=...`.
    *   `[ ]` Implement async state functions (if using async Redis lib like `redis-py`'s async API) or sync functions (if `redis-py` sync is used in userbot): `set_pending_prompt`, `get_pending_state` (returns `request_id`, `chat_id`), `clear_pending_state`, `store_request_data`, `update_request_status`, `get_request_data`. Handle `redis.exceptions.RedisError`.
2.  **[ ] Userbot Handlers (`app/userbot/handlers.py`):**
    *   `[ ]` Implement `handle_message_input(event)`:
        *   Check for pending state for user via `state.get_pending_state`.
        *   **If pending:** Treat message as prompt. Validate prompt. Store prompt via `state.store_request_data`. Clear pending state via `state.clear_pending_state`. Call `enqueue_processing_job`. Send "Queueing..." message, store its ID via `state.store_status_message`. Handle `/cancel` -> clear state, respond. Handle invalid replies.
        *   **If not pending:** Identify target chat ID from forward/text. Validate entity via `client.get_entity` (handle `ValueError`, permissions). If valid: generate `request_id`, store initial request data (`target_chat_id`, `status='PENDING_PROMPT'`) via `state.store_request_data`, set pending state via `state.set_pending_prompt_state`, reply asking for prompt. If invalid: send error message.
    *   `[ ]` Implement `async def enqueue_processing_job(user_id, target_chat_id, custom_prompt, request_id):`
        *   Get RQ Queue.
        *   Update request status in Redis to 'QUEUED' via `state.update_request_status`.
        *   Enqueue job `app.worker.tasks.extract_and_summarize_data`, passing all necessary args (`chat_id`, `session_path`, `user_id`, `request_id`, `custom_prompt`). Use job ID `f"extract:{request_id}:{target_chat_id}"`.
        *   Log enqueue. Store job ID in Redis (e.g., add field `rq_job_id` to `request:{request_id}:data` hash).
3.  **[ ] Register Handlers (`run_userbot.py`):** Ensure handlers registered.
4.  **[ ] Testing:** Unit test state functions (`fakeredis`). Integration test `handle_message_input` (mock Telethon client, use `fakeredis` for state, mock RQ enqueue). Test all conversational paths (valid chat -> prompt -> enqueue; valid chat -> cancel; invalid chat; invalid prompt response).
5.  **[ ] Manual Testing:** Deploy. Test full flow: send chat, reply prompt, check Redis state changes, check RQ queue for job. Test cancellation.

**End of Phase 2:** Userbot handles the complete input conversation via Telegram, managing state persistently in Redis and enqueueing jobs correctly.

---

## Phase 3: Worker - Extraction, Cleaning, LLM Call, Pub/Sub Notify

**Goal:** Implement the RQ worker task including history extraction, cleaning, LLM API interaction, temporary file saving (for participants), and notifying the Userbot of progress/completion via Redis Pub/Sub.

**Steps:**

1.  **[ ] LLM Service (`app/worker/llm_service.py`):**
    *   `[ ]` Implement `async def get_llm_summary(prompt: str, history_text: str, settings: config.Settings) -> Optional[str]:`
        *   Load API key/URL/model from `settings`.
        *   **Implement Truncation:** Estimate token count (simple word count * factor, or use `tiktoken` if added). If > `settings.MAX_LLM_HISTORY_TOKENS`, truncate `history_text` (e.g., keep beginning and end). Log truncation.
        *   Construct final prompt.
        *   Implement `httpx` API call logic with headers, body, timeout.
        *   Implement robust error handling for `httpx` errors and non-2xx responses. Log API errors.
        *   Parse response, extract summary. Return summary or `None`.
2.  **[ ] Worker Utils (`app/worker/utils.py`):** Implement/refine `clean_message_text`.
3.  **[ ] Worker Task (`app/worker/tasks.py`):**
    *   `[ ]` Import `get_redis_connection` and necessary modules.
    *   `[ ]` Define `extract_and_summarize_data(chat_id, user_session_path, user_id, request_id, custom_prompt):`
        *   Get Job ID. Get Redis connection: `redis_conn = get_redis_connection(config.settings)`.
        *   Define helper `def publish_status(status: str, detail: Optional[str] = None, progress: Optional[int] = None):` uses `redis_conn.publish(f"request_status:{request_id}", json.dumps({'job_id': job.id, 'chat_id': chat_id, 'status': status, 'detail': detail, 'progress': progress}))`. Include `try...except redis.RedisError`.
        *   **Main Logic (`try...finally` for client disconnect):**
            *   `publish_status('STARTED')`.
            *   Connect Telethon client. Check auth.
            *   `publish_status('EXTRACTING_HISTORY')`. Implement history extraction loop, accumulate `history_string`. Call `publish_status('PROGRESS', detail=f'{count} messages')` periodically. Handle errors/FloodWait (log, sleep, publish 'WAITING').
            *   `participants_text = None`. If group, `publish_status('EXTRACTING_PARTICIPANTS')`, implement participant extraction, format into `participants_text`. Handle errors.
            *   Disconnect Telethon client.
            *   If no `history_string`, raise `ValueError("No text history extracted.")`.
            *   `publish_status('CALLING_LLM')`. Call `llm_service.get_llm_summary` (handle potential `await` if service is async).
            *   If LLM fails (`summary is None`), raise `RuntimeError("LLM summarization failed.")`.
            *   **(Optional) Save participant text to temporary file:** If `participants_text`, save to unique file in `settings.OUTPUT_DIR_PATH`. Store path.
            *   `publish_status('SUCCESS')`.
            *   Return dict: `{'status': 'SUCCESS', 'summary': summary, 'participants_file': Optional[path], ...}` (Include request_id, user_id etc.).
        *   **Task Error Handling (`except Exception as e:`):**
            *   Log exception.
            *   `error_message = f"{type(e).__name__}: {str(e)}"`
            *   `publish_status('FAILED', detail=error_message)`
            *   Return dict: `{'status': 'FAILURE', 'error': error_message, ...}`.
4.  **[ ] Testing:** Unit test `llm_service` (mock `httpx`). Unit test `tasks.extract_and_summarize_data` (mock Telethon, LLM service, file I/O, Redis publish). Test truncation. Test all error paths and ensure correct status is published and dictionary returned.
5.  **[ ] Manual/Integration:** Trigger jobs. Check worker logs. Check Redis Pub/Sub channel (`redis-cli PSUBSCRIBE 'request_status:*'`) for status messages. Check job results in Redis. Check temporary participant file creation.

**End of Phase 3:** Worker extracts, cleans, calls LLM, saves temporary files, and notifies progress/completion via Redis Pub/Sub.

---

## Phase 4: Userbot - Handling Status Updates & Results Delivery

**Goal:** Implement logic in the userbot to listen to Redis Pub/Sub, update the user's status message in Telegram, and deliver the summary/files upon job completion.

**Steps:**

1.  **[ ] Pub/Sub Listener (`app/userbot/status_checker.py`):**
    *   `[ ]` Rename file/concept to `event_listener.py` or similar.
    *   `[ ]` Implement `async def listen_for_job_events(client):`
        *   Get Redis connection. `pubsub = redis_conn.pubsub(ignore_subscribe_messages=True)`.
        *   `await pubsub.psubscribe(f"request_status:*")`
        *   `logger.info("Subscribed to RQ job status updates via Redis Pub/Sub.")`
        *   `async for message in pubsub.listen():`
            *   `if message['type'] == 'pmessage':`
                *   `try:`
                    *   `data = json.loads(message['data'])`
                    *   `request_id = message['channel'].decode().split(':')[-1]`
                    *   `job_id = data.get('job_id')`
                    *   `chat_id = data.get('chat_id')`
                    *   `status = data.get('status')`
                    *   `detail = data.get('detail')`
                    *   `progress = data.get('progress')`
                    *   `logger.debug(f"Received status update: {data}")`
                    *   `# Update persistent state (e.g., update job status in request:{request_id} Hash)`
                    *   `await state.update_job_status_in_request(request_id, chat_id, status, detail, progress)`
                    *   `# Trigger UI update`
                    *   `await ui.update_status_message_for_request(client, request_id)`
                    *   `# If job is FINISHED (check status from task return, not just pubsub)`
                    *   `if status in ['SUCCESS', 'FAILED']:`
                         `await handle_job_completion(client, job_id, request_id, chat_id)` # Needs implementation
                *   `except json.JSONDecodeError:`
                    *   `logger.error(f"Failed to decode Pub/Sub message: {message['data']}")`
                *   `except Exception as e:`
                    *   `logger.exception(f"Error processing Pub/Sub message: {e}")`
2.  **[ ] Job Completion Handler (`app/userbot/event_listener.py` or `results_sender.py`):**
    *   `[ ]` Implement `async def handle_job_completion(client, job_id, request_id, chat_id):`
        *   Fetch job result from Redis: `job = Job.fetch(job_id, connection=...)`. Check status (`is_finished`, `is_failed`).
        *   Get `result_data = job.result`.
        *   Get `user_id` from request data in Redis: `user_id = await state.get_request_user_id(request_id)`.
        *   If `job.is_finished`:
            *   Call `results_sender.send_llm_result(client, user_id, chat_id, result_data)`.
        *   If `job.is_failed`:
            *   Call `results_sender.send_failure_message(client, user_id, chat_id, result_data)`.
        *   Update overall request status in Redis if all jobs for the request are done.
3.  **[ ] Results Sender (`app/userbot/results_sender.py`):**
    *   `[ ]` Implement `async def send_llm_result(client, user_id, chat_id, job_result_dict):`
        *   Extract `summary` and `participants_file` path from `job_result_dict`.
        *   Send summary message (handle length limits).
        *   If `participants_file` exists, `send_file`, then `os.remove` in `try...finally`.
    *   `[ ]` Implement `async def send_failure_message(client, user_id, chat_id, job_result_dict):`
        *   Extract `error` message.
        *   Send formatted error message to user.
4.  **[ ] UI Update Logic (`app/userbot/ui.py`):**
    *   `[ ]` Implement `async def update_status_message_for_request(client, request_id):`
        *   Get `user_id` and `status_message_id` from Redis state for the request.
        *   Get status of *all* jobs associated with the request from Redis state.
        *   Format a summary string (e.g., "Chat A: ✅, Chat B: ⏳ Extracting (500 msgs), Chat C: ❌ Failed").
        *   Call `client.edit_message` safely.
5.  **[ ] Start Listener (`run_userbot.py`):** Launch `listen_for_job_events(client)` as an asyncio task.
6.  **[ ] Testing:** Unit test Pub/Sub message handling, job completion logic, results sending (mock client, Redis, file ops).
7.  **[ ] Manual Testing:** Full end-to-end. Trigger jobs. Watch Telegram for initial message, progress edits, final summary message, and participant file (if applicable). Check file cleanup. Test failures.

**End of Phase 4:** Real-time (via Pub/Sub) status updates in Telegram. Summaries and participant files are delivered directly to the user upon job completion.

---

## Phase 5: Status Display & File Downloads

**Goal:** Implement the web UI for users to view the status of their requests/tasks dynamically and download the generated files securely.

**Steps:**

1.  **[ ] Schemas (`app/schemas.py`):** Define schemas for detailed request/task status responses.
2.  **[ ] CRUD (`app/crud.py`):** Add functions to query `ProcessingRequest` and associated `ChatTask` records by `request_id` or `user_id`. Add function to get `ChatTask` by ID/filename for download authorization.
3.  **[ ] Processing Router (`app/routers/processing.py`):**
    *   Implement `GET /status/{request_id}`: Renders the main status page template. Requires login & authorization (check if request belongs to user).
    *   Implement `GET /api/status/{request_id}`: Returns detailed JSON status of the request and its associated tasks (fetched from DB via `crud.py`). Requires login & authorization.
    *   Implement `GET /download/{task_db_id}/{filename}`: Requires login. Fetches `ChatTask` from DB by `task_db_id`. Verifies task belongs to logged-in user. Verifies `filename` matches stored path basename. Uses FastAPI's `FileResponse` to serve the file securely from `config.OUTPUT_DIR_PATH`. Handle `FileNotFoundError`.
4.  **[ ] Templates/Frontend (`app/templates/main/status.html`, static JS/htmx):**
    *   Status page fetches details from `/api/status/{request_id}` periodically using JS/htmx.
    *   Dynamically update the status display for each chat task (using icons, messages from DB).
    *   When a task status is 'SUCCESS', display download links pointing to `/download/{task_db_id}/{filename}`.
5.  **[ ] File Cleanup (Basic):** Consider adding logic (maybe a scheduled RQ job using `rq-scheduler` or a simple cron on the server) to delete files from `config.OUTPUT_DIR_PATH` older than X days.
6.  **[ ] Testing:** Unit test new CRUD functions. Integration test new API endpoints (status, download), including authorization checks and file serving. Test frontend JS/htmx polling and UI updates (manually or with frontend testing tools).
7.  **[ ] Manual Testing:** Deploy. Run jobs. Check status page updates dynamically. Verify download links appear and function correctly. Verify only the correct user can download files. Test error states display.

**End of Phase 5:** Users have a fully functional, hosted web application providing a seamless experience from login to downloading extracted Telegram data, with dynamic feedback. Further polishing (CSS, advanced features) can build on this.
