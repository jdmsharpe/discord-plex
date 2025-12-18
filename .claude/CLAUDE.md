# Project: Discord Plex Bot

Discord bot for Plex and Overseerr integration using py-cord.

## Architecture

```text
src/
  bot.py              # Entry point, bot setup
  config/auth.py      # Environment variable loading
  cogs/plex/
    cog.py            # Slash commands (/plex, /request)
    plex_client.py    # PlexAPI wrapper (extracts TMDB/IMDB IDs from GUIDs)
    overseerr_client.py # Async Overseerr API client (poster URLs, season info)
    cache.py          # In-memory library cache with fuzzy search
    models.py         # Dataclasses (CachedMedia, ActiveStream, etc.)
    views.py          # Discord UI components (selects, buttons, season picker)
    embeds.py         # Discord embed builders
```

## Key Patterns

- **py-cord 2.x**: Uses `discord.Bot`, `SlashCommandGroup`, `@option` decorators
- **Async**: Plex calls run in executor (`loop.run_in_executor`) since PlexAPI is sync
- **Caching**: `LibraryCache` holds all media with fuzzy search via `rapidfuzz`
- **TMDB Posters**: Plex items store `tmdb_id` extracted from GUIDs, posters fetched via Overseerr
- **Season Selection**: TV requests show `SeasonSelectView` to pick seasons before submitting
- **Repeatable Views**: UI components stay active after interaction (no disabling)

## Common Tasks

### Adding a new slash command

1. Add method in `cog.py` under appropriate command group (`plex` or `request`)
2. Use `@option()` decorator for parameters
3. Call `await ctx.defer()` for slow operations
4. Use `ctx.send_followup()` to respond

### Modifying embeds

Edit `embeds.py`. Functions like `create_media_embed()` return `discord.Embed`.

### Adding new data fields

1. Add field to dataclass in `models.py`
2. Populate in `plex_client.py` or `overseerr_client.py`
3. Display in `embeds.py`

## Testing

```bash
pytest tests/ -v  # 44 tests
```

Tests cover models, embeds, cache, and Overseerr client. No live API tests - mock PlexAPI/aiohttp for new tests.

CI runs on push/PR to `main` via GitHub Actions (`.github/workflows/ci.yml`).

## Environment Variables

Required: `BOT_TOKEN`, `GUILD_IDS`, `PLEX_URL`, `PLEX_TOKEN`, `OVERSEERR_URL`, `OVERSEERR_API_KEY`
Optional: `CACHE_REFRESH_MINUTES` (default 30), `ADMIN_USER_ID`
