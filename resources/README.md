# Resources Directory

This directory contains real, production-ready resource files for the Telegram Extractor & Summarizer Userbot.

## Contents

- **Language files:** All translations are stored as JSON files, e.g., `en.json`, `ru.json`.
- **Prompt templates:** System prompts and sample LLM templates, e.g., `summary_prompt.txt`.
- **Branding:** Icons, logos, or other images used in the userbot or web UI.

## Example: Language File

```json
{
  "START": "Welcome to the Telegram Summarizer!",
  "HELP": "Send me a chat or channel and a prompt, and I'll summarize it for you.",
  "ERROR": "Oops, something went wrong."
}
```

## Example: Prompt Template

`summary_prompt.txt`:
```
Summarize the following chat history for me. Highlight key events and participants.
Chat history:
{{CHAT_HISTORY}}
```

## Usage

- Resource files are loaded at runtime by helper functions.
- All string/template accesses must be robust and log errors if files are missing or malformed.

## Resource Loader (Fully Implemented)

```python
import os
import json
import logging

logger = logging.getLogger("resources.loader")

def load_language(lang_code, resources_dir="resources"):
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
    path = os.path.join(resources_dir, f"{template_name}.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            logger.info(f"Loaded prompt template: {path}")
            return content
    except Exception as e:
        logger.error(f"Failed to load prompt template {template_name}: {e}", exc_info=True)
        return ""
```
