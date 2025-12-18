import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import sys

sys.path.insert(0, "src")


class TestOverseerrClient(unittest.TestCase):
    """Tests for OverseerrClient methods."""

    def setUp(self):
        """Set up test fixtures."""
        # We need to mock the aiohttp session
        self.mock_session = MagicMock()
        self.mock_response = MagicMock()

    def test_get_poster_url_with_poster(self):
        """Test get_poster_url returns correct URL when poster exists."""
        # Import here to avoid discord import issues
        from cogs.plex.overseerr_client import OverseerrClient

        async def run_test():
            client = OverseerrClient("http://test:5055", "test-api-key")

            # Mock get_media_details to return poster data
            client.get_media_details = AsyncMock(
                return_value={"posterPath": "/abc123.jpg"}
            )

            result = await client.get_poster_url("movie", 12345)
            self.assertEqual(result, "https://image.tmdb.org/t/p/w500/abc123.jpg")

            await client.close()

        asyncio.run(run_test())

    def test_get_poster_url_no_poster(self):
        """Test get_poster_url returns None when no poster."""
        from cogs.plex.overseerr_client import OverseerrClient

        async def run_test():
            client = OverseerrClient("http://test:5055", "test-api-key")

            # Mock get_media_details to return no poster
            client.get_media_details = AsyncMock(return_value={"posterPath": None})

            result = await client.get_poster_url("movie", 12345)
            self.assertIsNone(result)

            await client.close()

        asyncio.run(run_test())

    def test_get_poster_url_no_details(self):
        """Test get_poster_url returns None when details fetch fails."""
        from cogs.plex.overseerr_client import OverseerrClient

        async def run_test():
            client = OverseerrClient("http://test:5055", "test-api-key")

            # Mock get_media_details to return None
            client.get_media_details = AsyncMock(return_value=None)

            result = await client.get_poster_url("movie", 12345)
            self.assertIsNone(result)

            await client.close()

        asyncio.run(run_test())

    def test_get_available_seasons(self):
        """Test _get_available_seasons extracts season numbers correctly."""
        from cogs.plex.overseerr_client import OverseerrClient

        async def run_test():
            client = OverseerrClient("http://test:5055", "test-api-key")

            # Mock get_media_details to return seasons
            client.get_media_details = AsyncMock(
                return_value={
                    "seasons": [
                        {"seasonNumber": 0, "episodeCount": 5},  # Specials - should be excluded
                        {"seasonNumber": 1, "episodeCount": 12},
                        {"seasonNumber": 2, "episodeCount": 10},
                    ]
                }
            )

            result = await client._get_available_seasons(12345)
            self.assertEqual(result, [1, 2])  # Should exclude season 0

            await client.close()

        asyncio.run(run_test())

    def test_get_available_seasons_empty(self):
        """Test _get_available_seasons returns empty list when no seasons."""
        from cogs.plex.overseerr_client import OverseerrClient

        async def run_test():
            client = OverseerrClient("http://test:5055", "test-api-key")

            # Mock get_media_details to return None
            client.get_media_details = AsyncMock(return_value=None)

            result = await client._get_available_seasons(12345)
            self.assertEqual(result, [])

            await client.close()

        asyncio.run(run_test())

    def test_create_request_with_seasons(self):
        """Test create_request includes seasons for TV shows."""
        from cogs.plex.overseerr_client import OverseerrClient

        async def run_test():
            client = OverseerrClient("http://test:5055", "test-api-key")

            # Track what was passed to _request
            request_calls = []

            async def mock_request(method, endpoint, json=None):
                request_calls.append({"method": method, "endpoint": endpoint, "json": json})
                return {
                    "id": 1,
                    "type": "tv",
                    "media": {"tmdbId": 12345},
                    "status": 1,
                    "requestedBy": {"displayName": "test"},
                    "createdAt": "2024-01-01T00:00:00Z",
                }

            client._request = mock_request

            await client.create_request("tv", 12345, seasons=[1, 2])

            # Verify seasons were included in the request
            self.assertEqual(len(request_calls), 1)
            self.assertEqual(request_calls[0]["json"]["seasons"], [1, 2])

            await client.close()

        asyncio.run(run_test())

    def test_create_request_auto_fetches_seasons(self):
        """Test create_request auto-fetches seasons for TV when not provided."""
        from cogs.plex.overseerr_client import OverseerrClient

        async def run_test():
            client = OverseerrClient("http://test:5055", "test-api-key")

            # Mock _get_available_seasons
            client._get_available_seasons = AsyncMock(return_value=[1, 2, 3])

            # Track what was passed to _request
            request_calls = []

            async def mock_request(method, endpoint, json=None):
                request_calls.append({"method": method, "endpoint": endpoint, "json": json})
                return {
                    "id": 1,
                    "type": "tv",
                    "media": {"tmdbId": 12345},
                    "status": 1,
                    "requestedBy": {"displayName": "test"},
                    "createdAt": "2024-01-01T00:00:00Z",
                }

            client._request = mock_request

            await client.create_request("tv", 12345)  # No seasons provided

            # Verify _get_available_seasons was called
            client._get_available_seasons.assert_called_once_with(12345)

            # Verify seasons were included in the request
            self.assertEqual(request_calls[0]["json"]["seasons"], [1, 2, 3])

            await client.close()

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()