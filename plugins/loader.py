import importlib
import os
import logging
from typing import Any

logger = logging.getLogger("plugins.loader")

def load_plugins(client: Any, plugins_dir: str = "plugins") -> int:
    """
    Loads all plugins with register(client), logs all activity/errors.
    Returns number of successfully loaded plugins.
    """
    logger.debug(f"[ENTRY] load_plugins(client={client}, plugins_dir={plugins_dir})")
    loaded = 0
    try:
        files = os.listdir(plugins_dir)
        logger.debug(f"Found files in plugins_dir: {files}")
        for fname in files:
            if fname.endswith(".py") and not fname.startswith("__"):
                modname = fname[:-3]
                try:
                    module = importlib.import_module(f"plugins.{modname}")
                    if hasattr(module, "register"):
                        module.register(client)
                        logger.info(f"Loaded plugin: {modname}")
                        loaded += 1
                    else:
                        logger.warning(f"Plugin {modname} has no register() function")
                except Exception as e:
                    logger.error(f"Failed to load plugin {modname}: {e}", exc_info=True)
        logger.debug(f"[EXIT] load_plugins: loaded={loaded}")
        return loaded
    except Exception as e:
        logger.error(f"[ERROR] Exception in load_plugins: {e}", exc_info=True)
        return loaded
