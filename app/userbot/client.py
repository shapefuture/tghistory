from telethon.sync import TelegramClient
from app.config import Settings
import logging

logger = logging.getLogger("userbot.client")

def get_telethon_client(settings: Settings):
    """
    Create a new Telethon client instance using configuration settings
    
    Args:
        settings: Application configuration settings
        
    Returns:
        TelegramClient: Unconnected Telethon client instance
    """
    logger.debug(f"Creating Telethon client: session_path={settings.TELEGRAM_SESSION_PATH}")
    
    try:
        # Create client instance
        client = TelegramClient(
            settings.TELEGRAM_SESSION_PATH,
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH,
        )
        
        logger.info(f"Successfully created Telethon client: session_path={settings.TELEGRAM_SESSION_PATH}")
        return client
    except ValueError as e:
        logger.error(f"Invalid parameter for Telethon client: {e}")
        raise
    except TypeError as e:
        logger.error(f"Wrong parameter type for Telethon client: {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error creating Telethon client: {e}")
        raise