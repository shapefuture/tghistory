import asyncio
import logging
import sys

from app.logging_config import setup_logging
from app import config
from app.userbot.client import get_telethon_client

def main():
    setup_logging(config.settings)
    client = get_telethon_client(config.settings)

    async def runner():
        try:
            await client.start()
        except Exception as e:
            logging.critical(f"❌ [Auth] Failed to start Telethon client: {e}", exc_info=True)
            sys.exit(1)

        if not await client.is_user_authorized():
            logging.critical(
                "❌ [Auth] User is NOT authorized. Session file might be invalid or missing. "
                "Please run interactively once via Render Shell or locally to authenticate."
            )
            sys.exit(1)

        logging.info(f"✅ [Userbot] Connected and authorized. Ready for action.")
        await client.run_until_disconnected()

    asyncio.run(runner())

if __name__ == "__main__":
    main()