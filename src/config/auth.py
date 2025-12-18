import os
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
ADMIN_ROLE_ID = (
    int(os.getenv("ADMIN_ROLE_ID", "0")) if os.getenv("ADMIN_ROLE_ID") else None
)
REQUEST_CHANNEL_ID = (
    int(os.getenv("REQUEST_CHANNEL_ID", "0"))
    if os.getenv("REQUEST_CHANNEL_ID")
    else None
)