#!/bin/bash
# Fully implemented: runs cleanup_old_files with logging, exits with status

set -e
cd "$(dirname "$0")/.."
LOGFILE="worker/cleanup_cron.log"
echo "[$(date)] Running cleanup_old_files.py" >> "$LOGFILE"
python3 worker/cleanup_old_files.py 3 >> "$LOGFILE" 2>&1
echo "[$(date)] Finished cleanup_old_files.py" >> "$LOGFILE"
