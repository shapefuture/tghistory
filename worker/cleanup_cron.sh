#!/bin/bash
# To be run as a cron job or Render Scheduled Job

cd "$(dirname "$0")/.."
python -m worker.cleanup_old_files