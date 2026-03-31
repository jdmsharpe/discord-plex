from discord import Bot, Intents

from discord_plex import PlexCog


def test_package_import_registers_cog():
    bot = Bot(intents=Intents.default())
    bot.add_cog(PlexCog(bot=bot))
    assert bot.get_cog("PlexCog") is not None
