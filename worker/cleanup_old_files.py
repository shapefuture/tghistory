import os
import time
import logging
from app import config

logger = logging.getLogger("worker.cleanup_old_files")

def cleanup_old_files(days=3):
    """Delete files in OUTPUT_DIR_PATH older than X days"""
    dir_path = config.settings.OUTPUT_DIR_PATH
    now = time.time()
    cutoff = now - days * 86400
    removed = 0
    for fname in os.listdir(dir_path):
        fpath = os.path.join(dir_path, fname)
        try:
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
                removed += 1
        except Exception as e:
            logger.error(f"Failed to remove {fpath}: {e}")
    logger.info(f"Cleanup complete. Files removed: {removed}")