import importlib

import pytest

import discord_plex.config.auth as auth


def _reload_auth_module(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("PLEX_TOKEN", "plex")
    monkeypatch.setenv("OVERSEERR_API_KEY", "key")
    return importlib.reload(auth)


def test_invalid_cache_refresh_minutes_uses_default_and_errors(monkeypatch, capsys):
    monkeypatch.setenv("CACHE_REFRESH_MINUTES", "not-a-number")

    reloaded = _reload_auth_module(monkeypatch)

    assert reloaded.CACHE_REFRESH_MINUTES == 30

    with pytest.raises(SystemExit):
        reloaded.validate_config()

    captured = capsys.readouterr()
    assert "Invalid configuration detected" in captured.err
    assert "CACHE_REFRESH_MINUTES must be an integer" in captured.err


def test_invalid_guild_ids_and_admin_user_id_errors(monkeypatch, capsys):
    monkeypatch.setenv("GUILD_IDS", "123,abc,456")
    monkeypatch.setenv("ADMIN_USER_ID", "oops")

    reloaded = _reload_auth_module(monkeypatch)

    assert reloaded.GUILD_IDS == [123, 456]
    assert reloaded.ADMIN_USER_ID is None

    with pytest.raises(SystemExit):
        reloaded.validate_config()

    captured = capsys.readouterr()
    assert "GUILD_IDS must be a comma-separated list of integers" in captured.err
    assert "ADMIN_USER_ID must be an integer" in captured.err
