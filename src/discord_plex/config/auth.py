import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV_VARS = ("BOT_TOKEN", "PLEX_TOKEN", "OVERSEERR_API_KEY")


def _get_env_or_none(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _parse_int_env(name: str, default: int | None = None) -> int | None:
    raw_value = _get_env_or_none(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid {name} value. Expected an integer, but received {raw_value!r}."
        ) from exc


def _parse_csv_int_env(name: str) -> list[int]:
    raw_value = os.getenv(name, "")
    if not raw_value.strip():
        return []

    values: list[int] = []
    for token in raw_value.split(","):
        stripped_token = token.strip()
        if not stripped_token:
            continue

        try:
            values.append(int(stripped_token))
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid {name} value. Expected a comma-separated list of integers, "
                f"but received invalid token: {stripped_token!r}."
            ) from exc

    return values


# Discord
BOT_TOKEN = _get_env_or_none("BOT_TOKEN")
GUILD_IDS = _parse_csv_int_env("GUILD_IDS")

# Plex
PLEX_URL = os.getenv("PLEX_URL", "http://localhost:32400")
PLEX_TOKEN = _get_env_or_none("PLEX_TOKEN")

# Overseerr
OVERSEERR_URL = os.getenv("OVERSEERR_URL", "http://localhost:5055")
OVERSEERR_API_KEY = _get_env_or_none("OVERSEERR_API_KEY")

# Optional Settings
CACHE_REFRESH_MINUTES = _parse_int_env("CACHE_REFRESH_MINUTES", default=30)
ADMIN_USER_ID = _parse_int_env("ADMIN_USER_ID", default=None)


def validate_required_config() -> None:
    missing_vars = [name for name in REQUIRED_ENV_VARS if _get_env_or_none(name) is None]
    if missing_vars:
        missing_list = ", ".join(missing_vars)
        raise RuntimeError(
            "Missing required environment configuration: "
            f"{missing_list}. Please set these variables before starting the bot."
        )
