# Fully implemented Dockerfile for production userbot + worker
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc build-essential libffi-dev libssl-dev git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create output and backup directories at build time
RUN mkdir -p /data/output /data/backups

# Default: start both userbot and worker in background
CMD bash -c "nohup python run_userbot.py >userbot.log 2>&1 & nohup python worker/run_worker.py >worker.log 2>&1 & tail -f userbot.log worker.log"
