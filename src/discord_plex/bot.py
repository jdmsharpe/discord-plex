"""Thin launcher for the discord-plex bot."""

import logging
import sys

from discord import Bot, Intents

from . import PlexCog
from .config import BOT_TOKEN, validate_config

logger = logging.getLogger(__name__)


def build_bot() -> Bot:
    validate_config()

    intents = Intents.default()
    intents.presences = False
    intents.members = True
    intents.message_content = True
    intents.guilds = True

    bot = Bot(intents=intents)
    bot.add_cog(PlexCog(bot=bot))

    @bot.event
    async def on_ready() -> None:
        logger.info("Logged in as %s", bot.user)
        logger.info("Connected to %s guilds", len(bot.guilds))

    @bot.event
    async def on_disconnect() -> None:
        logger.warning("Bot disconnected")

    return bot


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    bot = build_bot()
    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
