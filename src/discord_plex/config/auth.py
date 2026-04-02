import os
import sys

from dotenv import load_dotenv

load_dotenv()


_CONFIG_ERRORS: list[str] = []


def _parse_int_env(name: str, default: int | None = None, required: bool = False) -> int | None:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        if required and default is None:
            _CONFIG_ERRORS.append(f"- {name} is required and must be an integer.")
        return default

    try:
        return int(raw_value.strip())
    except ValueError:
        _CONFIG_ERRORS.append(
            f"- {name} must be an integer, but got {raw_value!r}.",
        )
        return default


def _parse_csv_int_env(name: str) -> list[int]:
    raw_value = os.getenv(name, "")
    if not raw_value.strip():
        return []

    values: list[int] = []
    invalid_values: list[str] = []
    for token in raw_value.split(","):
        token = token.strip()
        if not token:
            continue

        try:
            values.append(int(token))
        except ValueError:
            invalid_values.append(token)

    if invalid_values:
        _CONFIG_ERRORS.append(
            "- "
            f"{name} must be a comma-separated list of integers, but got invalid value(s): "
            + ", ".join(repr(value) for value in invalid_values)
            + ".",
        )

    return values


# Discord
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GUILD_IDS = _parse_csv_int_env("GUILD_IDS")

# Plex
PLEX_URL = os.getenv("PLEX_URL", "http://localhost:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN", "")

# Overseerr
OVERSEERR_URL = os.getenv("OVERSEERR_URL", "http://localhost:5055")
OVERSEERR_API_KEY = os.getenv("OVERSEERR_API_KEY", "")

# Optional Settings
CACHE_REFRESH_MINUTES = _parse_int_env("CACHE_REFRESH_MINUTES", default=30)
ADMIN_USER_ID = _parse_int_env("ADMIN_USER_ID", default=None)

_REQUIRED_VARS = {
    "BOT_TOKEN": BOT_TOKEN,
    "PLEX_TOKEN": PLEX_TOKEN,
    "OVERSEERR_API_KEY": OVERSEERR_API_KEY,
}


def validate_config() -> None:
    """Check that required environment variables are set. Call at bot startup."""
    missing = [name for name, val in _REQUIRED_VARS.items() if not val]
    errors: list[str] = []
    if missing:
        errors.append(
            "- Missing required environment variables: " + ", ".join(missing) + ".",
        )
    errors.extend(_CONFIG_ERRORS)

    if errors:
        print("ERROR: Invalid configuration detected.", file=sys.stderr)
        print("Please fix the following before restarting:", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        sys.exit(1)
