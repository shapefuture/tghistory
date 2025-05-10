import importlib
import os
import logging

logger = logging.getLogger("plugins.loader")

def load_plugins(client, plugins_dir="plugins"):
    """
    Fully implemented: loads all plugins with register(client), logs all activity/errors.
    """
    loaded = 0
    for fname in os.listdir(plugins_dir):
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
    logger.info(f"Total plugins loaded: {loaded}")
