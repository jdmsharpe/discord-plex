import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Discord
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GUILD_IDS = [
    int(id.strip()) for id in os.getenv("GUILD_IDS", "").split(",") if id.strip()
]

# Plex
PLEX_URL = os.getenv("PLEX_URL", "http://localhost:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN", "")

# Overseerr
OVERSEERR_URL = os.getenv("OVERSEERR_URL", "http://localhost:5055")
OVERSEERR_API_KEY = os.getenv("OVERSEERR_API_KEY", "")

# Optional Settings
CACHE_REFRESH_MINUTES = int(os.getenv("CACHE_REFRESH_MINUTES", "30"))
ADMIN_USER_ID = (
    int(os.getenv("ADMIN_USER_ID", "0")) if os.getenv("ADMIN_USER_ID") else None
)

_REQUIRED_VARS = {
    "BOT_TOKEN": BOT_TOKEN,
    "PLEX_TOKEN": PLEX_TOKEN,
    "OVERSEERR_API_KEY": OVERSEERR_API_KEY,
}


def validate_config() -> None:
    """Check that required environment variables are set. Call at bot startup."""
    missing = [name for name, val in _REQUIRED_VARS.items() if not val]
    if missing:
        print(
            f"ERROR: Missing required environment variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)
