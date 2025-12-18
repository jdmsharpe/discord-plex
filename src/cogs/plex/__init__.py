# Lazy import to avoid loading discord during tests
def __getattr__(name: str):
    if name == "PlexCog":
        from .cog import PlexCog
        return PlexCog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["PlexCog"]
