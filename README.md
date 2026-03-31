# Discord Plex Bot

![Badge](https://hitscounter.dev/api/hit?url=https%3A%2F%2Fgithub.com%2Fjdmsharpe%2Fdiscord-plex%2F&label=discord-plex&icon=github&color=%23198754&message=&style=flat&tz=UTC)
[![Docker CI](https://github.com/jdmsharpe/discord-plex/actions/workflows/main.yml/badge.svg)](https://github.com/jdmsharpe/discord-plex/actions/workflows/main.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)

A Discord bot for Plex and Overseerr integration. Search your library, view active streams, and request new media.

Supports Python 3.10+ locally and in CI.

## Features

- `/plex search <query>` - Search your Plex library with fuzzy matching (displays TMDB posters)
- `/plex playing` - View active streams with progress bars and transcode info
- `/plex recent` - Show recently added media
- `/plex stats` - Server statistics
- `/request search <query>` - Search TMDB and request new media via Overseerr
- `/request status` - View your requests
- `/request queue` - View pending requests (admin)
- `/request approve/deny` - Manage requests (admin)

**TV Show Requests**: When requesting a TV show, the bot prompts you to select which seasons to request.

## Setup

1. Copy `.env.example` to `.env` and fill in your values:

   ```ini
   BOT_TOKEN=your-discord-bot-token
   GUILD_IDS=123456789
   PLEX_URL=http://your-host:32400
   PLEX_TOKEN=your-plex-token
   OVERSEERR_URL=http://your-host:5055
   OVERSEERR_API_KEY=your-overseerr-api-key
   ```

2. Run with Docker:

   ```bash
   docker compose up -d --build
   ```

   Or locally:

   ```bash
   pip install -r requirements.txt
   python src/bot.py
   ```

   `src/bot.py` remains a thin repo-local launcher that delegates to `discord_plex.bot.main`.

### Using as a Cog

To compose this repo into a larger bot, import the namespaced package:

```python
from discord_plex import PlexCog

bot.add_cog(PlexCog(bot=bot))
```

Only `src/bot.py` remains at the repository root as a thin launcher; package code should be imported from `discord_plex`.

## Getting Tokens

- **Discord Bot Token**: [Discord Developer Portal](https://discord.com/developers/applications)
- **Plex Token**: Settings > Account > Authorized Devices, or via browser dev tools
- **Overseerr API Key**: Settings > General > API Key

## Development

### Testing

Tests use pytest with pytest-asyncio (`asyncio_mode = "auto"`). All tests are mocked — no real API calls. GitHub Actions runs the suite on Python 3.10, 3.11, 3.12, and 3.13.
The suite targets the namespaced package layout, with focused files such as `tests/test_cache.py`, `tests/test_embeds.py`, `tests/test_models.py`, `tests/test_overseerr_client.py`, and `tests/test_plex_client.py`.
`tests/test_package_import.py` is the package import smoke test.

```bash
# Run tests
python -m pytest -q

# Run tests in Docker
docker build --build-arg PYTHON_VERSION=3.13 -f Dockerfile.test -t discord-plex-test . && docker run --rm discord-plex-test

# Smoke-test another supported version
docker build --build-arg PYTHON_VERSION=3.10 -f Dockerfile.test -t discord-plex-test:3.10 . && docker run --rm discord-plex-test:3.10
```

### Linting & Type Checking

```bash
ruff check src/ tests/
ruff format src/ tests/
pyright src/
```

## CI

Tests run automatically on push/PR to `main` via GitHub Actions. CI runs `pytest` across Python 3.10-3.13, builds a Docker smoke test image, and only pushes the release image on direct pushes after both checks pass.
