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
    """Handle shutdown signals gracefully"""
    signal_name = {
        signal.SIGINT: "SIGINT",
        signal.SIGTERM: "SIGTERM",
    }.get(signum, str(signum))
    
    logger.info(f"Received {signal_name} signal. Shutting down gracefully...")
    # Exit with success code
    sys.exit(0)

async def scheduled_tasks(interval_minutes=60):
    """Run scheduled maintenance tasks periodically"""
    while True:
        try:
            # Backup session file every 24 hours (every 24th interval)
            if int(time.time() / 60) % (24 * 60) < interval_minutes:
                logger.info("Running scheduled session backup")
                success, result = BackupManager.backup_session_files()
                if success:
                    logger.info(f"Session backup created: {result}")
                else:
                    logger.error(f"Session backup failed: {result}")
            
            # Backup Redis data every 6 hours (every 6th interval)
            if int(time.time() / 60) % (6 * 60) < interval_minutes:
                logger.info("Running scheduled Redis backup")
                success, result = BackupManager.backup_redis_data()
                if success:
                    logger.info(f"Redis backup created: {result}")
                else:
                    logger.error(f"Redis backup failed: {result}")
            
            # Apply retention policy daily (every 24th interval)
            if int(time.time() / 60) % (24 * 60) < interval_minutes:
                logger.info("Applying backup retention policy")
                BackupManager.apply_retention_policy()
            
            # Cleanup old files daily (every 24th interval)
            if int(time.time() / 60) % (24 * 60) < interval_minutes:
                logger.info("Cleaning up old files")
                BackupManager.cleanup_old_files()
        
        except Exception as e:
            logger.error(f"Error in scheduled tasks: {e}")
        
        # Wait for next interval
        await asyncio.sleep(interval_minutes * 60)

def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    
    # Set up logging
    setup_logging(config.settings)
    
    # Create parent dirs for session and output
    os.makedirs(os.path.dirname(config.settings.TELEGRAM_SESSION_PATH), exist_ok=True)
    os.makedirs(config.settings.OUTPUT_DIR_PATH, exist_ok=True)
    
    # Get client
    client = get_telethon_client(config.settings)

    async def runner():
        try:
            # Connect to Telegram
            logger.info("Connecting to Telegram...")
            await client.start()
        except Exception as e:
            logger.critical(f"❌ [Auth] Failed to start Telethon client: {e}", exc_info=True)
            sys.exit(1)

        if not await client.is_user_authorized():
            logger.critical(
                "❌ [Auth] User is NOT authorized. Session file might be invalid or missing. "
                "Please run interactively once via Render Shell or locally to authenticate."
            )
            sys.exit(1)

        # Register message handlers
        logger.info("Registering message handlers...")
        register_handlers(client)
        
        # Start the Pub/Sub listener in the background
        logger.info("Starting Pub/Sub listener...")
        asyncio.create_task(listen_for_job_events(client))
        
        # Start scheduled tasks
        logger.info("Starting scheduled tasks...")
        asyncio.create_task(scheduled_tasks())

        # Record startup metrics
        me = await client.get_me()
        MetricsCollector.record_system_metrics()
        
        logger.info(f"✅ [Userbot] Connected and authorized as {me.first_name} (@{me.username}). Ready for action.")
        await client.run_until_disconnected()

    asyncio.run(runner())

if __name__ == "__main__":
    main()