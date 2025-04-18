import asyncio
import logging
import sys
import signal
import os

from app.logging_config import setup_logging
from app import config
from app.userbot.client import get_telethon_client
from app.userbot.handlers import register_handlers
from app.userbot.event_listener import listen_for_job_events

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

        logger.info(f"✅ [Userbot] Connected and authorized. Ready for action.")
        await client.run_until_disconnected()

    asyncio.run(runner())

if __name__ == "__main__":
    main()