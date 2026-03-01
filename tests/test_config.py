import os
import json
import pytest
from pydantic import ValidationError
from config import Settings, MinecraftServer


def test_legacy_env_variables(monkeypatch):
    """Test that legacy MC_SERVER_N_ variables are loaded correctly."""
    monkeypatch.setenv("DISCORD_TOKEN", "test")
    monkeypatch.setenv("CRAFTY_URL", "http://test")
    monkeypatch.setenv("CRAFTY_TOKEN", "test")
    monkeypatch.setenv("MC_SERVER_1_KEY", "uuid-1")
    monkeypatch.setenv("MC_SERVER_1_ID", "uuid-1")
    monkeypatch.setenv("MC_SERVER_1_NAME", "Vanilla")
    monkeypatch.setenv("MC_SERVER_2_KEY", "uuid-2")
    monkeypatch.setenv("MC_SERVER_2_ID", "uuid-2")
    monkeypatch.setenv("MC_SERVER_2_NAME", "Modded")

    settings = Settings()
    
    assert len(settings.servers) == 2
    assert "uuid-1" in settings.servers
    assert settings.servers["uuid-1"]["name"] == "Vanilla"
    assert "uuid-2" in settings.servers
    assert settings.servers["uuid-2"]["name"] == "Modded"


def test_json_env_variable(monkeypatch):
    """Test that MC_SERVERS_JSON takes precedence and parses correctly."""
    servers_data = [
        {"key": "json-id-1", "id": "json-id-1", "name": "JSON Server 1"},
        {"key": "json-id-2", "id": "json-id-2", "name": "JSON Server 2"}
    ]
    
    monkeypatch.setenv("DISCORD_TOKEN", "test")
    monkeypatch.setenv("CRAFTY_URL", "http://test")
    monkeypatch.setenv("CRAFTY_TOKEN", "test")
    # Set legacy variables that should be ignored
    monkeypatch.setenv("MC_SERVER_1_ID", "legacy-uuid")
    monkeypatch.setenv("MC_SERVER_1_NAME", "Legacy")
    # Set the JSON env var
    monkeypatch.setenv("MC_SERVERS_JSON", json.dumps(servers_data))

    settings = Settings()

    assert len(settings.servers) == 2
    assert "json-id-1" in settings.servers
    assert settings.servers["json-id-1"]["name"] == "JSON Server 1"
    assert "legacy-uuid" not in settings.servers


def test_invalid_json_env_variable(monkeypatch):
    """Test that invalid JSON falls back to empty servers instead of crashing blindly if required fields are missing."""
    monkeypatch.setenv("DISCORD_TOKEN", "test")
    monkeypatch.setenv("CRAFTY_URL", "http://test")
    monkeypatch.setenv("CRAFTY_TOKEN", "test")
    moon_data = [{"bad": "data"}]
    monkeypatch.setenv("MC_SERVERS_JSON", json.dumps(moon_data))

    settings = Settings()
    # It prints the error to stdout and falls back to other sources 
    # (resulting in empty dict if no legacy vars exists)
    assert settings.servers == {}
