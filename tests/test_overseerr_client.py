from unittest.mock import AsyncMock

from cogs.plex.overseerr_client import OverseerrClient


class TestOverseerrClient:
    """Tests for OverseerrClient methods."""

    async def test_get_poster_url_with_poster(self):
        client = OverseerrClient("http://test:5055", "test-api-key")
        client.get_media_details = AsyncMock(return_value={"posterPath": "/abc123.jpg"})

        result = await client.get_poster_url("movie", 12345)
        assert result == "https://image.tmdb.org/t/p/w500/abc123.jpg"
        await client.close()

    async def test_get_poster_url_no_poster(self):
        client = OverseerrClient("http://test:5055", "test-api-key")
        client.get_media_details = AsyncMock(return_value={"posterPath": None})

        result = await client.get_poster_url("movie", 12345)
        assert result is None
        await client.close()

    async def test_get_poster_url_no_details(self):
        client = OverseerrClient("http://test:5055", "test-api-key")
        client.get_media_details = AsyncMock(return_value=None)

        result = await client.get_poster_url("movie", 12345)
        assert result is None
        await client.close()

    async def test_get_available_seasons(self):
        client = OverseerrClient("http://test:5055", "test-api-key")
        client.get_media_details = AsyncMock(
            return_value={
                "seasons": [
                    {"seasonNumber": 0, "episodeCount": 5},
                    {"seasonNumber": 1, "episodeCount": 12},
                    {"seasonNumber": 2, "episodeCount": 10},
                ]
            }
        )

        result = await client._get_available_seasons(12345)
        assert result == [1, 2]
        await client.close()

    async def test_get_available_seasons_empty(self):
        client = OverseerrClient("http://test:5055", "test-api-key")
        client.get_media_details = AsyncMock(return_value=None)

        result = await client._get_available_seasons(12345)
        assert result == []
        await client.close()

    async def test_create_request_with_seasons(self):
        client = OverseerrClient("http://test:5055", "test-api-key")
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

        assert len(request_calls) == 1
        assert request_calls[0]["json"]["seasons"] == [1, 2]
        await client.close()

    async def test_create_request_auto_fetches_seasons(self):
        client = OverseerrClient("http://test:5055", "test-api-key")
        client._get_available_seasons = AsyncMock(return_value=[1, 2, 3])
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
        await client.create_request("tv", 12345)

        client._get_available_seasons.assert_called_once_with(12345)
        assert request_calls[0]["json"]["seasons"] == [1, 2, 3]
        await client.close()
