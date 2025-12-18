"""Utility functions for the Discord Plex bot."""

from typing import List


def chunk_text(text: str, chunk_size: int = 4096) -> List[str]:
    """
    Split text into chunks of specified size.

    Used for splitting long messages to fit Discord's embed limits.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    while text:
        if len(text) <= chunk_size:
            chunks.append(text)
            break

        # Try to split at newline
        split_idx = text.rfind("\n", 0, chunk_size)
        if split_idx == -1 or split_idx < chunk_size // 2:
            # No good newline, try space
            split_idx = text.rfind(" ", 0, chunk_size)
        if split_idx == -1 or split_idx < chunk_size // 2:
            # No good split point, force split
            split_idx = chunk_size

        chunks.append(text[:split_idx])
        text = text[split_idx:].lstrip()

    return chunks


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length with suffix."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_duration(milliseconds: int) -> str:
    """Format duration in milliseconds to human-readable string."""
    total_seconds = milliseconds // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_size(bytes_size: int) -> str:
    """Format file size in bytes to human-readable string."""
    size: float = float(bytes_size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
