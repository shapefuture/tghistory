import asyncio
import logging
import sys
import signal
import os
import time

from app.logging_config import setup_logging
from app import config
from app.userbot.client import get_telethon_client
from app.userbot.handlers import register_handlers
from app.userbot.event_listener import listen_for_job_events
from app.shared.metrics import MetricsCollector
from app.shared.backup import BackupManager

logger = logging.getLogger("userbot")

def handle_shutdown_signal(signum, frame):
    signal_name = {
        signal.SIGINT: "SIGINT",
        signal.SIGTERM: "SIGTERM",
    }.get(signum, str(signum))
    logger.info(f"Received {signal_name} signal. Shutting down gracefully...")
    sys.exit(0)

async def scheduled_tasks(interval_minutes=60):
    while True:
        try:
            now = int(time.time() / 60)
            if now % (24 * 60) < interval_minutes:
                logger.info("Running scheduled session backup")
                success, result = BackupManager.backup_session_files()
                if success:
                    logger.info(f"Session backup created: {result}")
                else:
                    logger.error(f"Session backup failed: {result}")
            if now % (6 * 60) < interval_minutes:
                logger.info("Running scheduled Redis backup")
                success, result = BackupManager.backup_redis_data()
                if success:
                    logger.info(f"Redis backup created: {result}")
                else:
                    logger.error(f"Redis backup failed: {result}")
            if now % (24 * 60) < interval_minutes:
                logger.info("Applying backup retention policy")
                BackupManager.apply_retention_policy()
            if now % (24 * 60) < interval_minutes:
                logger.info("Cleaning up old files")
                BackupManager.cleanup_old_files()
        except Exception as e:
            logger.error(f"Error in scheduled tasks: {e}", exc_info=True)
        await asyncio.sleep(interval_minutes * 60)

def main():
    try:
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
        setup_logging(config.settings)
        os.makedirs(os.path.dirname(config.settings.TELEGRAM_SESSION_PATH), exist_ok=True)
        os.makedirs(config.settings.OUTPUT_DIR_PATH, exist_ok=True)
        client = get_telethon_client(config.settings)
        async def runner():
            try:
                logger.info("Connecting to Telegram...")
                await client.start()
            except Exception as e:
                logger.critical(f"❌ [Auth] Failed to start Telethon client: {e}", exc_info=True)
                sys.exit(1)
            try:
                if not await client.is_user_authorized():
                    logger.critical(
                        "❌ [Auth] User is NOT authorized. Session file might be invalid or missing. "
                        "Please run interactively once via Render Shell or locally to authenticate."
                    )
                    sys.exit(1)
            except Exception as e:
                logger.critical(f"❌ [Auth] User authorization check failed: {e}", exc_info=True)
                sys.exit(1)
            try:
                logger.info("Registering message handlers...")
                register_handlers(client)
            except Exception as e:
                logger.critical(f"❌ [Handler] Failed to register handlers: {e}", exc_info=True)
                sys.exit(1)
            try:
                logger.info("Starting Pub/Sub listener...")
                asyncio.create_task(listen_for_job_events(client))
                logger.info("Starting scheduled tasks...")
                asyncio.create_task(scheduled_tasks())
                me = await client.get_me()
                MetricsCollector.record_system_metrics()
                logger.info(f"✅ [Userbot] Connected and authorized as {me.first_name} (@{me.username}). Ready for action.")
                await client.run_until_disconnected()
            except Exception as e:
                logger.critical(f"Fatal error in userbot runner: {e}", exc_info=True)
                sys.exit(1)
        asyncio.run(runner())
    except Exception as e:
        logger.critical(f"Userbot main failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
