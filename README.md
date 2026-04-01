# Discord Plex Bot

![Hits](https://hitscounter.dev/api/hit?url=https%3A%2F%2Fgithub.com%2Fjdmsharpe%2Fdiscord-plex%2F&label=discord-plex&icon=github&color=%23198754&message=&style=flat&tz=UTC)
[![Docker CI](https://github.com/jdmsharpe/discord-plex/actions/workflows/main.yml/badge.svg)](https://github.com/jdmsharpe/discord-plex/actions/workflows/main.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)

## Overview
A Discord bot built for seamless Plex and Overseerr integration. It allows users to search your media library, view active streams, and request new media directly from Discord using modern slash commands. 

## Features
- **Library Integration:** Search your Plex library with fuzzy matching and view TMDB posters.
- **Stream Monitoring:** View currently active Plex streams complete with progress bars and transcoding information.
- **Media Requests:** Search TMDB and request new movies or TV shows via Overseerr.
- **Interactive TV Show Requests:** When requesting a TV show, the bot actively prompts you to select which specific seasons to request.
- **Admin Management:** View pending requests and approve or deny them directly within Discord.
- **Server Stats:** Quickly check recently added media and overall server statistics.

## Commands

### `/plex` Commands
* **`/plex search <query>`**: Search your Plex library with fuzzy matching.
* **`/plex playing`**: View active streams with progress bars and transcode info.
* **`/plex recent`**: Show recently added media.
* **`/plex stats`**: Display Plex server statistics.

### `/request` Commands
* **`/request search <query>`**: Search TMDB and request new media via Overseerr.
* **`/request status`**: View the status of your personal requests.
* **`/request queue`**: View all pending requests *(Admin only)*.
* **`/request approve` / `/request deny`**: Manage and moderate requests *(Admin only)*.

## Setup & Installation

### Prerequisites
- Python 3.10+
- Discord Bot Token
- Plex Server & Token
- Overseerr Server & API Key

### Installation
1. Clone the repository and navigate to the project directory.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the environment example file:
   ```bash
   cp .env.example .env
   ```

### Configuration (`.env`)
| Variable | Required | Description |
| --- | --- | --- |
| `BOT_TOKEN` | **Yes** | Your Discord bot token |
| `GUILD_IDS` | **Yes** | Comma-separated Discord server IDs |
| `PLEX_URL` | **Yes** | URL to your Plex server (e.g., `http://your-host:32400`) |
| `PLEX_TOKEN` | **Yes** | Your Plex authentication token |
| `OVERSEERR_URL` | **Yes** | URL to your Overseerr instance (e.g., `http://your-host:5055`) |
| `OVERSEERR_API_KEY` | **Yes** | Your Overseerr API key |

### Running the Bot
**Locally:**
```bash
python src/bot.py
```
*(Note: `src/bot.py` is a thin launcher that delegates to `discord_plex.bot.main`)*

**With Docker:**
```bash
docker compose up -d --build
```

**Using as a Cog:**
To compose this repo into a larger bot, import the namespaced package:
```python
from discord_plex import PlexCog

bot.add_cog(PlexCog(bot=bot))
```

## Discord Bot & Service Setup

### Getting Your Tokens
* **Discord Bot Token**: Go to the [Discord Developer Portal](https://discord.com/developers/applications), create an application, add a bot, and copy the token.
* **Plex Token**: In Plex, go to Settings > Account > Authorized Devices, or extract it via your browser's developer tools.
* **Overseerr API Key**: In Overseerr, go to Settings > General > API Key.

## Usage
1. Use the `/plex` commands to explore your current library and monitor server activity.
2. Use the `/request` commands to search for new content. If requesting a TV show, click the interactive buttons to specify which seasons you want.
3. Server administrators can use `/request queue` and the approve/deny commands to manage inbound Overseerr requests without leaving Discord.

## Development

### Testing
Tests use `pytest` with `pytest-asyncio` (`asyncio_mode = "auto"`). All tests are mocked (no real API calls). 
```bash
# Run tests locally
python -m pytest -q

# Run tests in Docker
docker build --build-arg PYTHON_VERSION=3.13 -f Dockerfile.test -t discord-plex-test . 
docker run --rm discord-plex-test

# Smoke-test another supported version
docker build --build-arg PYTHON_VERSION=3.10 -f Dockerfile.test -t discord-plex-test:3.10 . 
docker run --rm discord-plex-test:3.10
```

### Linting & Type Checking
```bash
ruff check src/ tests/
ruff format src/ tests/
pyright src/
```

### CI
Tests run automatically on push/PR to `main` via GitHub Actions. CI runs `pytest` across Python 3.10-3.13, builds a Docker smoke test image, and only pushes the release image on direct pushes after both checks pass.
