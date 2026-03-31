# Discord Plex Bot - Developer Reference

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
