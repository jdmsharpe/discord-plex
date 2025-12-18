# Project: Discord Plex Bot

Discord bot for Plex and Overseerr integration using py-cord.

## Architecture

```
src/
  bot.py              # Entry point, bot setup
  config/auth.py      # Environment variable loading
  cogs/plex/
    cog.py            # Slash commands (/plex, /request)
    plex_client.py    # PlexAPI wrapper
    overseerr_client.py # Async Overseerr API client
    cache.py          # In-memory library cache with fuzzy search
    models.py         # Dataclasses (CachedMedia, ActiveStream, etc.)
    views.py          # Discord UI components (selects, buttons)
    embeds.py         # Discord embed builders
```

## Key Patterns

- **py-cord 2.x**: Uses `discord.Bot`, `SlashCommandGroup`, `@option` decorators
- **Async**: Plex calls run in executor (`loop.run_in_executor`) since PlexAPI is sync
- **Caching**: `LibraryCache` holds all media with fuzzy search via `rapidfuzz`
- **TMDB Posters**: Plex items store `tmdb_id` extracted from GUIDs, posters fetched from Overseerr

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
pytest tests/ -v
```

Tests cover models, embeds, and cache. No live API tests - mock PlexAPI for new tests.

## Environment Variables

Required: `BOT_TOKEN`, `GUILD_IDS`, `PLEX_URL`, `PLEX_TOKEN`, `OVERSEERR_URL`, `OVERSEERR_API_KEY`
Optional: `CACHE_REFRESH_MINUTES` (default 30), `ADMIN_USER_ID`