# Telegram Extraction Userbot

A userbot solution to extract, analyze, and summarize Telegram chats using LLM technology.

## Features

- Extract message history from Telegram chats, groups, and channels
- Extract participant information from groups
- Summarize content using LLM APIs
- Real-time status updates during processing
- Redis state management for robustness
- Background job processing with RQ

## Environment Setup

This project supports both new and legacy environment variable naming:

| New Name | Legacy Name | Description |
|----------|-------------|-------------|
| TELEGRAM_API_ID | API_ID | Telegram API ID (required) |
| TELEGRAM_API_HASH | API_HASH | Telegram API hash (required) |
| TELEGRAM_SESSION_PATH | SESSION | Path to session file (required) |
| REDIS_URL | REDIS_URI | Redis connection URL (required) |
| OUTPUT_DIR_PATH | - | Path for output files (default: /data/output) |
| LOG_LEVEL | - | Logging level (default: INFO) |
| RQ_QUEUE_NAME | - | Redis queue name (default: default) |
| LLM_API_KEY | - | LLM API key (optional) |
| LLM_ENDPOINT_URL | - | LLM API endpoint (optional) |
| LLM_MODEL_NAME | - | LLM model name (optional) |
| MAX_LLM_HISTORY_TOKENS | - | Max tokens for LLM (default: 3000) |

Copy `.env.sample` to `.env` and fill in the values.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# First-time interactive authentication
python run_userbot.py

# Start the worker
python worker/run_worker.py
```

## Usage

1. Send a message to yourself with a chat/group/channel name or forward a message from the target.
2. Respond with your custom prompt when asked.
3. Wait for the extraction and summarization to complete.
4. Receive a summary and participant file (if applicable).

## Deployment

This project includes a `render.yaml` for easy deployment on Render.com.

## Security Warning

The authentication in API endpoints is a placeholder only. Before production deployment, implement proper authentication using OAuth2, JWT, or a similar system.

## License

See the LICENSE file for details.