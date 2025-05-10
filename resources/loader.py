import os
import json
import logging
from typing import Dict

logger = logging.getLogger("resources.loader")

def load_language(lang_code: str, resources_dir: str = "resources") -> Dict:
    """
    Loads language file, logs all errors, returns dict.
    """
    logger.debug(f"[ENTRY] load_language(lang_code={lang_code}, resources_dir={resources_dir})")
    path = os.path.join(resources_dir, f"{lang_code}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Loaded language file: {path}")
            logger.debug(f"[EXIT] load_language: keys={list(data.keys())}")
            return data
    except Exception as e:
        logger.error(f"Failed to load language file {lang_code}: {e}", exc_info=True)
        return {}

def load_prompt_template(template_name: str, resources_dir: str = "resources") -> str:
    """
    Loads prompt template, logs all errors, returns string.
    """
    logger.debug(f"[ENTRY] load_prompt_template(template_name={template_name}, resources_dir={resources_dir})")
    path = os.path.join(resources_dir, f"{template_name}.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            logger.info(f"Loaded prompt template: {path}")
            logger.debug(f"[EXIT] load_prompt_template: len={len(content)}")
            return content
    except Exception as e:
        logger.error(f"Failed to load prompt template {template_name}: {e}", exc_info=True)
        return ""
