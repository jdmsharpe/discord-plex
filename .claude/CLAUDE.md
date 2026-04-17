# Discord Plex Bot - Developer Reference

## Dev Setup

```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env  # fill in required values
```

## Environment Variables

Required (bot exits at startup if missing):

| Variable | Description |
| -------- | ----------- |
| `BOT_TOKEN` | Discord bot token |
| `PLEX_TOKEN` | Plex Media Server token |
| `OVERSEERR_API_KEY` | Overseerr API key |

Optional (have defaults):

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `GUILD_IDS` | *(empty)* | Comma-separated guild IDs for guild-scoped slash commands |
| `PLEX_URL` | `http://localhost:32400` | Plex server URL |
| `OVERSEERR_URL` | `http://localhost:5055` | Overseerr URL |
| `CACHE_REFRESH_MINUTES` | `30` | Library cache TTL |
| `ADMIN_USER_ID` | *(none)* | Discord user ID for admin-only commands |
| `LOG_FORMAT` | `text` | Set to `json` for structured JSON-lines output |

## Docker

```bash
docker compose up -d    # build and start
docker compose logs -f  # tail logs
```

> If Plex/Overseerr run in Docker too, put all containers on the same network (see comment in `docker-compose.yaml`).

## Gotchas

- Uses **`py-cord`** (not `discord.py`). The slash-command API differs; don't mix docs between the two.
- `GUILD_IDS` empty → commands register globally (up to 1-hour propagation delay). Set it to a test guild ID during development for instant updates.

## Supported Entry Points

- Launcher: `python src/bot.py` remains supported and delegates to `discord_plex.bot.main`.
- Cog composition contract:

  ```python
  from discord_plex import PlexCog

  bot.add_cog(PlexCog(bot=bot))
  ```

## Package Layout

```text
src/
├── bot.py                           # Thin repo-local launcher
└── discord_plex/
    ├── __init__.py
    ├── bot.py
    ├── logging_setup.py             # Structured logging + request-id ContextVar
    ├── util.py
    ├── config/
    │   ├── __init__.py
    │   └── auth.py
    └── cogs/
        ├── __init__.py
        └── plex/
            ├── __init__.py
            ├── cache.py
            ├── cog.py
            ├── embeds.py
            ├── library.py
            ├── models.py
            ├── overseerr_client.py
            ├── plex_client.py
            ├── requests.py
            └── views.py
```

Only `src/bot.py` remains at the repo root; code imports should target `discord_plex...`.

## Testing And Patch Targets

- `pytest` runs with `pythonpath = ["src"]`.
- The test suite targets the namespaced package layout under `discord_plex...`.
- `tests/test_package_import.py` is the package import smoke test.
- New tests and patches should target real owners under `discord_plex...`.
- Examples:
  - `discord_plex.cogs.plex.cache.LibraryCache`
  - `discord_plex.cogs.plex.overseerr_client.OverseerrClient`
  - `discord_plex.cogs.plex.plex_client.PlexClientWrapper`
  - `discord_plex.cogs.plex.embeds.create_media_embed`

## Validation Commands

```bash
ruff check src/ tests/
ruff format src/ tests/
pyright src/
pytest -q
```

## Provider Notes

- `discord_plex.cogs.plex.cog` owns cog lifecycle and slash-command registration.
- Plex library command flows are delegated through `discord_plex.cogs.plex.library`.
- Overseerr request command flows are delegated through `discord_plex.cogs.plex.requests`.
- Keep `python src/bot.py` working when refactoring further.

## Runtime Conventions (Cross-Project)

- Unlike the AI bots in this family, discord-plex does not use a pricing YAML — it has no token-based API costs.
- The repo pre-commit hook (`.githooks/pre-commit`) runs `ruff format` (auto-applied + re-staged), then `ruff check` (blocking), then `pyright` and `pytest --collect-only` as warning-only smoke tests. Resolves tools from `.venv/bin` or `.venv/Scripts` first, then `PATH`.
- **Request IDs**: `cog_before_invoke` binds a fresh 8-char hex id via `discord_plex.logging_setup.bind_request_id` on every slash command. All downstream `logger.info`/`warning`/`error` calls automatically include the id. Set `LOG_FORMAT=json` for JSON-lines output.
