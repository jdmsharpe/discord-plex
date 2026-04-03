import importlib
import sys
from types import ModuleType

import pytest

MODULE_NAME = "discord_plex.config.auth"


def _import_fresh_auth_module(monkeypatch: pytest.MonkeyPatch):
    sys.modules.pop(MODULE_NAME, None)
    dotenv_module = ModuleType("dotenv")
    dotenv_module.load_dotenv = lambda *_, **__: None
    monkeypatch.setitem(sys.modules, "dotenv", dotenv_module)
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("PLEX_TOKEN", "plex")
    monkeypatch.setenv("OVERSEERR_API_KEY", "key")
    return importlib.import_module(MODULE_NAME)


def test_validate_required_config_reports_missing_vars(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("PLEX_TOKEN", raising=False)
    monkeypatch.delenv("OVERSEERR_API_KEY", raising=False)

    auth = _import_fresh_auth_module(monkeypatch)

    with pytest.raises(RuntimeError, match="BOT_TOKEN, PLEX_TOKEN, OVERSEERR_API_KEY"):
        auth.validate_required_config()


def test_validate_required_config_rejects_whitespace_only_values(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "   ")
    monkeypatch.setenv("PLEX_TOKEN", "\t")
    monkeypatch.setenv("OVERSEERR_API_KEY", " ")

    auth = _import_fresh_auth_module(monkeypatch)

    with pytest.raises(RuntimeError, match="BOT_TOKEN, PLEX_TOKEN, OVERSEERR_API_KEY"):
        auth.validate_required_config()


def test_validate_required_config_allows_present_vars(monkeypatch):
    auth = _import_fresh_auth_module(monkeypatch)

    auth.validate_required_config()


def test_invalid_cache_refresh_minutes_raises_clear_error(monkeypatch):
    monkeypatch.setenv("CACHE_REFRESH_MINUTES", "not-a-number")

    with pytest.raises(RuntimeError, match="Invalid CACHE_REFRESH_MINUTES value"):
        _import_fresh_auth_module(monkeypatch)


def test_invalid_guild_ids_raise_clear_error(monkeypatch):
    monkeypatch.setenv("GUILD_IDS", "123,abc,456")

    with pytest.raises(RuntimeError, match="invalid token: 'abc'"):
        _import_fresh_auth_module(monkeypatch)


def test_invalid_admin_user_id_raises_clear_error(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_ID", "oops")

    with pytest.raises(RuntimeError, match="Invalid ADMIN_USER_ID value"):
        _import_fresh_auth_module(monkeypatch)


def test_guild_ids_parsing_ignores_whitespace_and_empty_tokens(monkeypatch):
    monkeypatch.setenv("GUILD_IDS", " 123 , , 456 ,   ")

    auth = _import_fresh_auth_module(monkeypatch)

    assert auth.GUILD_IDS == [123, 456]
