# Plugins Directory

This directory contains fully implemented plugins and extensions for the Telegram Extractor & Summarizer Userbot system.

## How to Use

- Place any Python plugin file (ending in `.py`) in this directory.
- Plugins can extend userbot behavior, add new commands, or integrate with external services.
- Plugins are loaded at runtime by importing all `.py` files found here.

## Example Plugin

Create a file like `plugins/echo.py`:

```python
from telethon import events

def register(client):
    @client.on(events.NewMessage(pattern="/echo"))
    async def echo_handler(event):
        await event.respond(f"Echo: {event.raw_text}")
```

## Plugin Loader (Fully Implemented)

You may use the following loader to import all plugins at startup:

```python
import importlib
import os
import logging

logger = logging.getLogger("plugins.loader")

def load_plugins(client, plugins_dir="plugins"):
    for fname in os.listdir(plugins_dir):
        if fname.endswith(".py") and not fname.startswith("__"):
            modname = fname[:-3]
            try:
                module = importlib.import_module(f"plugins.{modname}")
                if hasattr(module, "register"):
                    module.register(client)
                    logger.info(f"Loaded plugin: {modname}")
            except Exception as e:
                logger.error(f"Failed to load plugin {modname}: {e}", exc_info=True)
```

## Guidelines

- All plugins must have a `register(client)` function.
- Logging and exception handling must be robust.
- Plugins should NOT block the main event loop.

