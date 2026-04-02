import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from discord_plex.cogs.plex.cache import LibraryCache
from discord_plex.cogs.plex.models import CachedMedia, MediaType


class TestLibraryCache:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_plex_client = MagicMock()
        self.cache = LibraryCache(self.mock_plex_client, refresh_minutes=30)
        self.test_media = [
            CachedMedia(
                rating_key="1",
                title="Breaking Bad",
                year=2008,
                media_type=MediaType.SHOW,
                library="TV Shows",
            ),
            CachedMedia(
                rating_key="2",
                title="Better Call Saul",
                year=2015,
                media_type=MediaType.SHOW,
                library="TV Shows",
            ),
            CachedMedia(
                rating_key="3",
                title="The Matrix",
                year=1999,
                media_type=MediaType.MOVIE,
                library="Movies",
            ),
            CachedMedia(
                rating_key="4",
                title="Interstellar",
                year=2014,
                media_type=MediaType.MOVIE,
                library="Movies",
            ),
        ]

    def _populate_cache(self):
        for item in self.test_media:
            self.cache._cache[item.rating_key] = item
            self.cache._index_title(item)
        self.cache._last_refresh = datetime.now()

    def test_is_stale_when_never_refreshed(self):
        assert self.cache.is_stale is True

    def test_is_stale_when_recently_refreshed(self):
        self.cache._last_refresh = datetime.now()
        assert self.cache.is_stale is False

    def test_is_stale_when_old(self):
        self.cache._last_refresh = datetime.now() - timedelta(minutes=60)
        assert self.cache.is_stale is True

    def test_get_by_key(self):
        self._populate_cache()
        item = self.cache.get_by_key("1")
        assert item is not None
        assert item.title == "Breaking Bad"

    def test_get_by_key_not_found(self):
        self._populate_cache()
        item = self.cache.get_by_key("999")
        assert item is None

    def test_search_exact_match(self):
        self._populate_cache()
        results = self.cache.search("Breaking Bad")
        assert len(results) > 0
        assert results[0].title == "Breaking Bad"

    def test_search_fuzzy_match(self):
        self._populate_cache()
        results = self.cache.search("braking bad")
        assert len(results) > 0
        assert results[0].title == "Breaking Bad"

    def test_search_with_type_filter(self):
        self._populate_cache()
        results = self.cache.search("matrix", media_type=MediaType.MOVIE)
        assert len(results) == 1
        assert results[0].title == "The Matrix"

    def test_search_with_library_filter(self):
        self._populate_cache()
        results = self.cache.search("breaking", library="TV Shows")
        assert len(results) > 0
        assert results[0].media_type == MediaType.SHOW

    def test_search_no_results(self):
        self._populate_cache()
        results = self.cache.search("xyznonexistent")
        assert len(results) == 0

    def test_get_libraries(self):
        self._populate_cache()
        libraries = self.cache.get_libraries()
        assert "TV Shows" in libraries
        assert "Movies" in libraries

    def test_get_stats(self):
        self._populate_cache()
        stats = self.cache.get_stats()

        assert set(stats.keys()) == {
            "total_items",
            "by_type",
            "by_library",
            "last_refresh",
            "is_stale",
        }
        assert stats["total_items"] == 4
        assert isinstance(stats["total_items"], int)
        assert isinstance(stats["by_type"], dict)
        assert isinstance(stats["by_library"], dict)
        assert isinstance(stats["last_refresh"], str)
        assert isinstance(stats["is_stale"], bool)
        assert stats["by_type"]["show"] == 2
        assert stats["by_type"]["movie"] == 2
        assert stats["by_library"]["TV Shows"] == 2
        assert stats["by_library"]["Movies"] == 2
        assert stats["last_refresh"] is not None

    @pytest.mark.asyncio
    async def test_shutdown_cancels_background_refresh_task(self):
        self.mock_plex_client.get_all_media.return_value = []

        await self.cache.start_background_refresh()
        refresh_task = self.cache._refresh_task

        assert refresh_task is not None

        # Let the loop run once so task enters its sleep cycle
        await asyncio.sleep(0.05)

        await self.cache.shutdown()

        assert self.cache._refresh_task is None
        assert refresh_task.done()
        assert refresh_task.cancelled()
