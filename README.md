# Discord Plex Bot

![Badge](https://hitscounter.dev/api/hit?url=https%3A%2F%2Fgithub.com%2Fjdmsharpe%2Fdiscord-plex%2F&label=discord-plex&icon=github&color=%23198754&message=&style=flat&tz=UTC)
[![Docker CI](https://github.com/jdmsharpe/discord-plex/actions/workflows/main.yml/badge.svg)](https://github.com/jdmsharpe/discord-plex/actions/workflows/main.yml)

A Discord bot for Plex and Overseerr integration. Search your library, view active streams, and request new media.

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

## Getting Tokens

- **Discord Bot Token**: [Discord Developer Portal](https://discord.com/developers/applications)
- **Plex Token**: Settings > Account > Authorized Devices, or via browser dev tools
- **Overseerr API Key**: Settings > General > API Key

## Development

```bash
# Create venv
python -m venv .venv
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install deps
pip install -r requirements.txt

# Run tests (132 tests)
pytest tests/ -v
```

## CI

Tests run automatically on push/PR to `main` via GitHub Actions. The workflow runs pytest in a Docker container.
