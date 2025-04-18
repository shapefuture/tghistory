# Telegram Extractor & Summarizer Userbot

## 1. Project Architecture

This project implements a Telegram userbot that can extract chat history, process through an LLM, and return summaries. It uses a distributed architecture with Redis as both state management and message queue system.

### Core Components:

1. **Userbot (Frontend)**: Telegram client that handles user commands, manages state via Redis, and presents results.
2. **RQ Worker (Backend)**: Processes extraction jobs, calls LLM APIs, and notifies frontend via Redis Pub/Sub.
3. **Redis**: Used for state management, job queuing, and real-time notifications.
4. **API/Web UI**: Optional FastAPI-based status viewing and file download functionality.

### Flow:
1. User specifies chat (forward or link)
2. User provides custom prompt
3. Job is queued in Redis
4. Worker extracts chat history
5. Worker calls LLM API
6. Results returned via Telegram
7. (Optional) Files available for download via web

## 2. Configuration & Setup

### `app/config.py`
- **`Settings` class**: Pydantic BaseSettings for robust configuration validation
  - Validates API keys, path existence, URL formats
  - Throws clear error messages on misconfiguration

### `app/logging_config.py`
- **`setup_logging(settings)`**: Configures Python logging and structlog
  - Sets appropriate log levels from configuration
  - Formats logs consistently

### `app/shared/redis_client.py`
- **`get_redis_connection(settings)`**: Creates and validates Redis connection
  - Uses connection pooling via global instance
  - Handles connection errors gracefully
- **`get_rq_queue(redis_conn, settings)`**: Creates RQ queue for job management

## 3. Redis State Management

### `app/userbot/state.py`
- **`set_pending_prompt_state(user_id, request_id)`**: Marks user as awaiting prompt
- **`get_pending_state(user_id)`**: Retrieves pending request ID for user
- **`clear_pending_state(user_id)`**: Clears pending state
- **`set_status_message(user_id, chat_id, message_id)`**: Stores ID of status message
- **`get_status_message(user_id, chat_id)`**: Retrieves status message ID
- **`store_request_data(request_id, data)`**: Stores request details in Redis hash
- **`update_request_status(request_id, status)`**: Updates job status
- **`get_request_data(request_id)`**: Retrieves full request details
- **`add_rq_job_id(request_id, rq_job_id)`**: Associates RQ job with request

All functions handle Redis exceptions gracefully, preventing app crashes.

## 4. Userbot Components

### `app/userbot/client.py`
- **`get_telethon_client(settings)`**: Creates Telethon client with config

### `app/userbot/handlers.py`
- **`register_handlers(client)`**: Sets up Telethon event handlers
- **`handle_message_input(event)`**: Core handler for all user messages
  - Detects chat specification vs prompt input
  - Manages conversation state via Redis
  - Validates input
  - Generates request IDs
- **`enqueue_processing_job(event, user_id, request_id, prompt)`**: Queues extraction job
  - Creates and stores RQ job
  - Updates status

### `app/userbot/event_listener.py`
- **`listen_for_job_events(client)`**: Subscribes to Redis Pub/Sub
  - Processes real-time worker updates
  - Triggers UI updates and result delivery
- **`handle_job_completion(client, job_id, request_id, chat_id)`**: Handles finished jobs
  - Fetches results from Redis
  - Triggers appropriate sender

### `app/userbot/results_sender.py`
- **`send_llm_result(client, user_id, chat_id, job_result_dict)`**: Sends success results
  - Handles long messages by splitting
  - Manages file sending
- **`send_failure_message(client, user_id, chat_id, job_result_dict)`**: Sends failure notices

### `app/userbot/ui.py`
- **`update_status_message_for_request(client, request_id)`**: Updates status message
  - Fetches latest job state
  - Edits existing message

### `run_userbot.py`
- **`main()`**: Entry point for userbot
  - Sets up logging
  - Authenticates Telethon
  - Starts event loop

## 5. Worker Components

### `app/worker/tasks.py`
- **`extract_and_summarize_data(chat_id, user_session_path, user_id, request_id, custom_prompt)`**: Main RQ job
  - Extracts chat history via Telethon
  - Processes participants list
  - Calls LLM
  - Saves results
  - Publishes status updates

### `app/worker/llm_service.py`
- **`estimate_token_count(text)`**: Estimates token count for LLM context management
- **`truncate_history(history_text, max_tokens)`**: Ensures history fits into context window
- **`get_llm_summary(prompt, history_text, settings)`**: Makes LLM API call
  - Handles errors
  - Formats request

### `app/worker/utils.py`
- **`clean_message_text(text)`**: Cleans Telegram message artifacts

### `worker/cleanup_old_files.py`
- **`cleanup_old_files(days=3)`**: Removes old temporary files

### `worker/run_worker.py`
- **`main()`**: Entry point for worker
  - Sets up RQ worker
  - Connects to Redis

## 6. API/Web Components

### `app/schemas.py`
- **`TaskStatusSchema`**: Pydantic model for task status
- **`ProcessingRequestSchema`**: Pydantic model for request status

### `app/crud.py`
- **`get_processing_request(request_id)`**: Fetches request data for API

### `app/routers/processing.py`
- **`api_status(request_id, user)`**: API for status updates
- **`status_page(request_id, user)`**: Web page for status monitoring
- **`download_file(task_id, filename, user)`**: Secure file downloads

## 7. Testing Framework

Comprehensive test suite covering:
- Configuration validation
- Redis state management
- Message handling
- LLM service functionality
- Worker task execution
- Results delivery

## 8. Deployment

### `render.yaml`
- Defines infrastructure for Render.com:
  - Redis service
  - Userbot worker
  - RQ worker
  - Shared persistent storage
  - Environment variables

## Usage Flow

1. Send a chat username, link, or forward a message
2. Respond with custom prompt (or `/cancel`)
3. View progress updates in Telegram
4. Receive summary and participant lists directly in Telegram
5. (Optional) View detailed status and download files via web UI