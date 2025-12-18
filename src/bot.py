import asyncio
import logging
import sys

from discord import Bot, Intents

from config.auth import BOT_TOKEN
from cogs.plex import PlexCog


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point."""
    # Configure intents
    intents = Intents.default()
    intents.presences = False
    intents.members = True
    intents.message_content = True
    intents.guilds = True

    # Create bot
    bot = Bot(intents=intents)

    # Add cog
    plex_cog = PlexCog(bot)
    bot.add_cog(plex_cog)

    @bot.event
    async def on_ready() -> None:
        logger.info(f"Logged in as {bot.user}")
        logger.info(f"Connected to {len(bot.guilds)} guilds")

    @bot.event
    async def on_disconnect() -> None:
        logger.warning("Bot disconnected")

    await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())