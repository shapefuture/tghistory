from telethon.sync import TelegramClient
from app.config import Settings

def get_telethon_client(settings: Settings):
    # Returns an unconnected client instance
    return TelegramClient(
        settings.TELEGRAM_SESSION_PATH,
        settings.TELEGRAM_API_ID,
        settings.TELEGRAM_API_HASH,
    )