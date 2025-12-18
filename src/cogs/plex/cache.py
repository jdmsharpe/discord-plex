import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from rapidfuzz import fuzz, process

from .models import CachedMedia, MediaType
from .plex_client import PlexClientWrapper


logger = logging.getLogger(__name__)


class LibraryCache:
    """In-memory cache of Plex library with fuzzy search capabilities."""

    def __init__(self, plex_client: PlexClientWrapper, refresh_minutes: int = 30):
        self.plex_client = plex_client
        self.refresh_minutes = refresh_minutes
        self._cache: dict[str, CachedMedia] = {}  # rating_key -> CachedMedia
        self._title_index: dict[str, list[str]] = (
            {}
        )  # normalized_title -> [rating_keys]
        self._last_refresh: Optional[datetime] = None
        self._refresh_lock = asyncio.Lock()
        self._refresh_task: Optional[asyncio.Task] = None

    @property
    def is_stale(self) -> bool:
        """Check if cache needs refresh."""
        if self._last_refresh is None:
            return True
        return datetime.now() - self._last_refresh > timedelta(
            minutes=self.refresh_minutes
        )

    @property
    def item_count(self) -> int:
        """Get number of cached items."""
        return len(self._cache)

    async def start_background_refresh(self) -> None:
        """Start periodic background refresh task."""
        if self._refresh_task is not None:
            return

        async def refresh_loop():
            while True:
                try:
                    await self.refresh()
                except Exception as e:
                    logger.error(f"Background cache refresh error: {e}")
                await asyncio.sleep(self.refresh_minutes * 60)

        self._refresh_task = asyncio.create_task(refresh_loop())
        logger.info("Started background cache refresh task")

    def stop_background_refresh(self) -> None:
        """Stop the background refresh task."""
        if self._refresh_task:
            self._refresh_task.cancel()
            self._refresh_task = None
            logger.info("Stopped background cache refresh task")

    async def refresh(self) -> None:
        """Refresh the cache from Plex."""
        async with self._refresh_lock:
            logger.info("Refreshing library cache...")
            start_time = datetime.now()

            try:
                # Run blocking Plex API call in executor
                loop = asyncio.get_event_loop()
                media_items = await loop.run_in_executor(
                    None,
                    self.plex_client.get_all_media,
                )

                # Clear and rebuild cache
                self._cache.clear()
                self._title_index.clear()

                for item in media_items:
                    self._cache[item.rating_key] = item
                    self._index_title(item)

                self._last_refresh = datetime.now()
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(
                    f"Cache refreshed: {len(self._cache)} items in {elapsed:.2f}s"
                )

            except Exception as e:
                logger.error(f"Failed to refresh cache: {e}")
                raise

    def _index_title(self, item: CachedMedia) -> None:
        """Add item to title index for fuzzy search."""
        normalized = self._normalize_title(item.title)
        if normalized not in self._title_index:
            self._title_index[normalized] = []
        self._title_index[normalized].append(item.rating_key)

        # Also index with year appended
        if item.year:
            with_year = f"{normalized} {item.year}"
            if with_year not in self._title_index:
                self._title_index[with_year] = []
            self._title_index[with_year].append(item.rating_key)

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize title for indexing."""
        return title.lower().strip()

    def get_by_key(self, rating_key: str) -> Optional[CachedMedia]:
        """Get item by rating key."""
        return self._cache.get(rating_key)

    def search(
        self,
        query: str,
        limit: int = 10,
        media_type: Optional[MediaType] = None,
        library: Optional[str] = None,
    ) -> list[CachedMedia]:
        """
        Fuzzy search the cache.

        Args:
            query: Search query
            limit: Maximum results to return
            media_type: Filter by media type
            library: Filter by library name

        Returns:
            List of matching CachedMedia sorted by relevance
        """
        if not self._cache:
            return []

        normalized_query = self._normalize_title(query)

        # Get all titles for fuzzy matching
        titles = list(self._title_index.keys())

        # Use rapidfuzz to find best matches
        # token_set_ratio handles partial matches well (e.g., "jujutsu" matches "jujutsu kaisen")
        matches = process.extract(
            normalized_query,
            titles,
            scorer=fuzz.token_set_ratio,
            limit=limit * 2,  # Get extra to account for filtering
        )

        results = []
        seen_keys = set()

        for title, score, _ in matches:
            # Higher threshold (70) for tighter matching - prevents unrelated results
            if score < 70:
                continue

            rating_keys = self._title_index.get(title, [])
            for rating_key in rating_keys:
                if rating_key in seen_keys:
                    continue

                item = self._cache.get(rating_key)
                if not item:
                    continue

                # Apply filters
                if media_type and item.media_type != media_type:
                    continue
                if library and item.library.lower() != library.lower():
                    continue

                seen_keys.add(rating_key)
                results.append((score, item))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)

        return [item for _, item in results[:limit]]

    def get_recently_added(
        self,
        limit: int = 10,
        library: Optional[str] = None,
    ) -> list[CachedMedia]:
        """Get recently added items from cache."""
        items = list(self._cache.values())

        # Filter by library if specified
        if library:
            items = [i for i in items if i.library.lower() == library.lower()]

        # Sort by added_at descending
        items.sort(
            key=lambda x: x.added_at if x.added_at else datetime.min,
            reverse=True,
        )

        return items[:limit]

    def get_libraries(self) -> list[str]:
        """Get unique library names from cache."""
        libraries = set()
        for item in self._cache.values():
            libraries.add(item.library)
        return sorted(libraries)

    def get_all(
        self,
        media_type: Optional[MediaType] = None,
        library: Optional[str] = None,
    ) -> list[CachedMedia]:
        """Get all items, optionally filtered."""
        items = list(self._cache.values())

        if media_type:
            items = [i for i in items if i.media_type == media_type]
        if library:
            items = [i for i in items if i.library.lower() == library.lower()]

        return items

    def get_stats(self) -> dict:
        """Get cache statistics."""
        type_counts = {}
        library_counts = {}

        for item in self._cache.values():
            # Count by type
            type_name = item.media_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

            # Count by library
            library_counts[item.library] = library_counts.get(item.library, 0) + 1

        return {
            "total_items": len(self._cache),
            "by_type": type_counts,
            "by_library": library_counts,
            "last_refresh": (
                self._last_refresh.isoformat() if self._last_refresh else None
            ),
            "is_stale": self.is_stale,
        }
