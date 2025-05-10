import os
import json
import pytest
import resources.loader

def test_load_language_success(tmp_path):
    lang = {"HELLO": "Hello World!"}
    path = tmp_path / "en.json"
    path.write_text(json.dumps(lang))
    result = resources.loader.load_language("en", resources_dir=str(tmp_path))
    assert result == lang

def test_load_language_missing(tmp_path):
    result = resources.loader.load_language("doesnotexist", resources_dir=str(tmp_path))
    assert result == {}

def test_load_prompt_template_success(tmp_path):
    prompt = "Summarize this: {{TEXT}}"
    path = tmp_path / "summary_prompt.txt"
    path.write_text(prompt)
    result = resources.loader.load_prompt_template("summary_prompt", resources_dir=str(tmp_path))
    assert result == prompt

def test_load_prompt_template_missing(tmp_path):
    result = resources.loader.load_prompt_template("notfound", resources_dir=str(tmp_path))
    assert result == ""
