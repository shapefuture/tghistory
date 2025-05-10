import os
import time
import logging
from app import config

logger = logging.getLogger("worker.cleanup_old_files")

def cleanup_old_files(days=3):
    """
    Delete files in OUTPUT_DIR_PATH older than X days.
    Fully implemented: traverses output directory, logs all activity, deletes only files older than cutoff.
    """
    dir_path = config.settings.OUTPUT_DIR_PATH
    now = time.time()
    cutoff = now - days * 86400
    removed = 0
    checked = 0
    errors = 0

    logger.info(f"Starting cleanup_old_files: directory={dir_path}, days={days}, cutoff_epoch={cutoff}")
    if not os.path.exists(dir_path):
        logger.warning(f"Output directory does not exist: {dir_path}")
        return 0

    for fname in os.listdir(dir_path):
        fpath = os.path.join(dir_path, fname)
        try:
            if os.path.isfile(fpath):
                checked += 1
                mtime = os.path.getmtime(fpath)
                if mtime < cutoff:
                    os.remove(fpath)
                    logger.info(f"Deleted old file: {fpath} (mtime={mtime})")
                    removed += 1
                else:
                    logger.debug(f"File recent, not deleted: {fpath} (mtime={mtime})")
        except Exception as e:
            logger.error(f"Failed to check/delete file {fpath}: {e}", exc_info=True)
            errors += 1

    logger.info(f"Old file cleanup complete: checked={checked}, removed={removed}, errors={errors}")
    return removed

if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    removed = cleanup_old_files(days=days)
    print(f"Removed {removed} old files from output directory.")
