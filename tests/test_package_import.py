import importlib
import sys
from types import ModuleType

from discord import Bot, Intents


def test_package_import_registers_cog(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "discord-token")
    monkeypatch.setenv("PLEX_TOKEN", "plex-token")
    monkeypatch.setenv("OVERSEERR_API_KEY", "overseerr-key")

    dotenv_module = ModuleType("dotenv")
    dotenv_module.load_dotenv = lambda *_, **__: None
    monkeypatch.setitem(sys.modules, "dotenv", dotenv_module)

    for module_name in (
        "discord_plex.config.auth",
        "discord_plex.config",
        "discord_plex.cogs.plex",
        "discord_plex.cogs",
        "discord_plex.cogs.plex.cog",
        "discord_plex",
    ):
        sys.modules.pop(module_name, None)

    PlexCog = importlib.import_module("discord_plex").PlexCog

    bot = Bot(intents=Intents.default())
    bot.add_cog(PlexCog(bot=bot))
    assert bot.get_cog("PlexCog") is not None
