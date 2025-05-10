import os
import types
import sys
import pytest

import plugins.loader

class DummyClient:
    def __init__(self):
        self.loaded = []

@pytest.fixture
def dummy_plugin(tmp_path, monkeypatch):
    plugin_code = """
def register(client):
    client.loaded.append("echo")
"""
    pluginfile = tmp_path / "echo.py"
    pluginfile.write_text(plugin_code)
    monkeypatch.syspath_prepend(str(tmp_path))
    return tmp_path

def test_load_plugins_loads_plugins(monkeypatch, dummy_plugin):
    client = DummyClient()
    # Patch importlib to import from dummy_plugin dir
    import importlib
    import sys
    sys.path.insert(0, str(dummy_plugin))
    plugins_dir = str(dummy_plugin)
    plugins.loader.load_plugins(client, plugins_dir=plugins_dir)
    assert "echo" in client.loaded

def test_load_plugins_handles_missing_register(tmp_path):
    plugin_code = "def not_register(client): pass"
    pluginfile = tmp_path / "bad.py"
    pluginfile.write_text(plugin_code)
    client = DummyClient()
    plugins.loader.load_plugins(client, plugins_dir=str(tmp_path))
    # Should not raise, just log
    assert client.loaded == []

def test_load_plugins_handles_import_error(tmp_path):
    # Create a plugin file with syntax error
    pluginfile = tmp_path / "bad2.py"
    pluginfile.write_text("def register(client):\n  raise Exception('fail')\n")
    client = DummyClient()
    plugins.loader.load_plugins(client, plugins_dir=str(tmp_path))
    # Should not raise
    assert client.loaded == []
