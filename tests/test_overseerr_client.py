from unittest.mock import AsyncMock

import pytest

from discord_plex.cogs.plex.overseerr_client import OverseerrClient, OverseerrError


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

    async def test_search_passes_raw_query_to_request_params(self):
        client = OverseerrClient("http://test:5055", "test-api-key")
        request_calls = []
        raw_query = "Star Wars: A New Hope + Special"

        async def mock_request(method, endpoint, json=None, params=None, raise_on_error=False):
            request_calls.append(
                {"method": method, "endpoint": endpoint, "json": json, "params": params}
            )
            return {"results": []}

        client._request = mock_request
        await client.search(raw_query, page=3)

        assert len(request_calls) == 1
        assert request_calls[0]["params"] == {"query": raw_query, "page": 3}
        await client.close()

    async def test_search_percent_encodes_spaces_in_url(self):
        # Seerr 3.4.1 rejects '+'-encoded spaces with HTTP 400
        # "Parameter 'query' must be url encoded", so the query must reach the
        # wire percent-encoded. aiohttp's params= mapping would emit '+'.
        client = OverseerrClient("http://test:5055", "test-api-key")
        requested_urls = []

        class _Response:
            status = 200

            async def json(self):
                return {"results": []}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

        class _Session:
            closed = False

            def request(self, method, url, **kwargs):
                requested_urls.append(url)
                assert "params" not in kwargs, "params= re-encodes spaces as '+'"
                return _Response()

        client._session = _Session()
        await client.search("steins;gate 0")

        assert len(requested_urls) == 1
        url = requested_urls[0]
        assert "query=steins%3Bgate%200" in url
        assert "+" not in url
        assert "%25" not in url, "query must not be double-encoded"

    async def test_search_raises_on_api_error(self):
        # A rejecting or unreachable server must not look like an empty result
        # set; request_search renders a distinct error embed for OverseerrError.
        client = OverseerrClient("http://test:5055", "test-api-key")

        async def failing_request(method, endpoint, json=None, params=None, raise_on_error=False):
            assert raise_on_error is True
            raise OverseerrError("HTTP 400: Parameter 'query' must be url encoded")

        client._request = failing_request

        with pytest.raises(OverseerrError):
            await client.search("steins gate")
        await client.close()

    async def test_search_returns_empty_on_no_results(self):
        client = OverseerrClient("http://test:5055", "test-api-key")

        async def empty_request(method, endpoint, json=None, params=None, raise_on_error=False):
            return {"results": []}

        client._request = empty_request

        assert await client.search("nothing matches this") == []
        await client.close()
