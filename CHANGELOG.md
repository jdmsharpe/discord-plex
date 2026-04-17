# Changelog

## v1.1.0

### feat
- add `src/discord_plex/logging_setup.py` exposing `REQUEST_ID` ContextVar, `bind_request_id()`, and `configure_logging()` for structured logging with per-request IDs
- bind a fresh 8-char hex request id in `cog_before_invoke` so every slash command invocation is traceable across downstream `logger` calls
- support `LOG_FORMAT=json` to emit JSON-lines output suitable for log aggregators (defaults to human-readable text)
- adopt canonical `.githooks/pre-commit` hook (previously missing): `ruff format` (auto-applied + re-staged), `ruff check` (blocking), `pyright` (warning-only), and `pytest --collect-only` (warning-only smoke), byte-identical to the sibling discord-* repos

### fix
- untrack `.serena/` tool cache that was accidentally committed in the main overhaul commit

### chore
- bump project version to `1.1.0`
- add `.serena/` and `.codex/` to `.gitignore` so tool artifacts stay out of future commits

### test
- add 8 new tests in `tests/test_logging_setup.py` covering `REQUEST_ID` ContextVar defaults, `bind_request_id()` behavior, `configure_logging()` wiring, and `LOG_FORMAT=json` output
- total test count goes from 144 to 152

### docs
- refresh `README.md` with the new `LOG_FORMAT` environment variable
- update `.claude/CLAUDE.md` with the `LOG_FORMAT` env var, the `logging_setup.py` module in the package layout, and runtime conventions covering request IDs and the pre-commit hook
- refresh `.env.example` with `LOG_FORMAT`

### compare
- [`v1.0.2...v1.1.0`](https://github.com/jdmsharpe/discord-plex/compare/v1.0.2...v1.1.0)
