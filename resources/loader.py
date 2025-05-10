import os
import json
import logging

logger = logging.getLogger("resources.loader")

def load_language(lang_code, resources_dir="resources"):
    """
    Fully implemented: loads language file, logs all errors, returns dict.
    """
    path = os.path.join(resources_dir, f"{lang_code}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Loaded language file: {path}")
            return data
    except Exception as e:
        logger.error(f"Failed to load language file {lang_code}: {e}", exc_info=True)
        return {}

def load_prompt_template(template_name, resources_dir="resources"):
    """
    Fully implemented: loads prompt template, logs all errors, returns string.
    """
    path = os.path.join(resources_dir, f"{template_name}.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            logger.info(f"Loaded prompt template: {path}")
            return content
    except Exception as e:
        logger.error(f"Failed to load prompt template {template_name}: {e}", exc_info=True)
        return ""
