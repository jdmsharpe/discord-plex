import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

import sys

sys.path.insert(0, "src")

from cogs.plex.models import CachedMedia, MediaType
from cogs.plex.cache import LibraryCache


class TestLibraryCache(unittest.TestCase):
    def setUp(self):
        self.mock_plex_client = MagicMock()
        self.cache = LibraryCache(self.mock_plex_client, refresh_minutes=30)

        # Add some test data
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
        """Manually populate cache for testing."""
        for item in self.test_media:
            self.cache._cache[item.rating_key] = item
            self.cache._index_title(item)
        self.cache._last_refresh = datetime.now()

    def test_is_stale_when_never_refreshed(self):
        self.assertTrue(self.cache.is_stale)

    def test_is_stale_when_recently_refreshed(self):
        self.cache._last_refresh = datetime.now()
        self.assertFalse(self.cache.is_stale)

    def test_is_stale_when_old(self):
        self.cache._last_refresh = datetime.now() - timedelta(minutes=60)
        self.assertTrue(self.cache.is_stale)

    def test_get_by_key(self):
        self._populate_cache()
        item = self.cache.get_by_key("1")
        self.assertIsNotNone(item)
        self.assertEqual(item.title, "Breaking Bad")

    def test_get_by_key_not_found(self):
        self._populate_cache()
        item = self.cache.get_by_key("999")
        self.assertIsNone(item)

    def test_search_exact_match(self):
        self._populate_cache()
        results = self.cache.search("Breaking Bad")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].title, "Breaking Bad")

    def test_search_fuzzy_match(self):
        self._populate_cache()
        results = self.cache.search("braking bad")  # Typo
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].title, "Breaking Bad")

    def test_search_with_type_filter(self):
        self._populate_cache()
        results = self.cache.search("matrix", media_type=MediaType.MOVIE)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "The Matrix")

    def test_search_with_library_filter(self):
        self._populate_cache()
        results = self.cache.search("breaking", library="TV Shows")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].media_type, MediaType.SHOW)

    def test_search_no_results(self):
        self._populate_cache()
        results = self.cache.search("xyznonexistent")
        self.assertEqual(len(results), 0)

    def test_get_libraries(self):
        self._populate_cache()
        libraries = self.cache.get_libraries()
        self.assertIn("TV Shows", libraries)
        self.assertIn("Movies", libraries)

    def test_get_stats(self):
        self._populate_cache()
        stats = self.cache.get_stats()
        self.assertEqual(stats["total_items"], 4)
        self.assertIn("by_type", stats)
        self.assertIn("by_library", stats)
        self.assertEqual(stats["by_type"]["show"], 2)
        self.assertEqual(stats["by_type"]["movie"], 2)


if __name__ == "__main__":
    unittest.main()
