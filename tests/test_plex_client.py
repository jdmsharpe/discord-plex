import sys
import unittest
from unittest.mock import MagicMock, PropertyMock

sys.path.insert(0, "src")

from cogs.plex.models import MediaType, PlexClient


class TestPlexClientWrapperInit(unittest.TestCase):
    """Tests for PlexClientWrapper initialization."""

    def _make_client(self, base_url="http://localhost:32400", token="test-token"):
        from cogs.plex.plex_client import PlexClientWrapper

        return PlexClientWrapper(base_url, token)

    def test_strips_trailing_slash(self):
        client = self._make_client("http://localhost:32400/")
        self.assertEqual(client.base_url, "http://localhost:32400")

    def test_stores_token(self):
        client = self._make_client(token="my-token")
        self.assertEqual(client.token, "my-token")

    def test_server_initially_none(self):
        client = self._make_client()
        self.assertIsNone(client._server)

    def test_reconnect_clears_server(self):
        client = self._make_client()
        client._server = MagicMock()
        client.reconnect()
        self.assertIsNone(client._server)


class TestGetThumbUrl(unittest.TestCase):
    def _make_client(self):
        from cogs.plex.plex_client import PlexClientWrapper

        return PlexClientWrapper("http://plex:32400", "tok123")

    def test_returns_full_url(self):
        client = self._make_client()
        result = client.get_thumb_url("/library/metadata/123/thumb/abc")
        self.assertEqual(
            result,
            "http://plex:32400/library/metadata/123/thumb/abc?X-Plex-Token=tok123",
        )

    def test_returns_none_for_none(self):
        client = self._make_client()
        self.assertIsNone(client.get_thumb_url(None))

    def test_returns_none_for_empty_string(self):
        client = self._make_client()
        self.assertIsNone(client.get_thumb_url(""))


class TestGetMediaType(unittest.TestCase):
    def _get_media_type(self, plex_type):
        from cogs.plex.plex_client import PlexClientWrapper

        return PlexClientWrapper._get_media_type(plex_type)

    def test_movie(self):
        self.assertEqual(self._get_media_type("movie"), MediaType.MOVIE)

    def test_show(self):
        self.assertEqual(self._get_media_type("show"), MediaType.SHOW)

    def test_episode(self):
        self.assertEqual(self._get_media_type("episode"), MediaType.EPISODE)

    def test_season(self):
        self.assertEqual(self._get_media_type("season"), MediaType.SEASON)

    def test_artist(self):
        self.assertEqual(self._get_media_type("artist"), MediaType.ARTIST)

    def test_album(self):
        self.assertEqual(self._get_media_type("album"), MediaType.ALBUM)

    def test_track(self):
        self.assertEqual(self._get_media_type("track"), MediaType.TRACK)

    def test_unknown_returns_none(self):
        self.assertIsNone(self._get_media_type("photo"))

    def test_empty_returns_none(self):
        self.assertIsNone(self._get_media_type(""))


class TestExtractExternalIds(unittest.TestCase):
    def _make_client(self):
        from cogs.plex.plex_client import PlexClientWrapper

        return PlexClientWrapper("http://plex:32400", "tok")

    def _make_item_with_guids(self, guid_ids):
        """Create a mock item with a list of guid IDs."""
        item = MagicMock()
        guids = []
        for gid in guid_ids:
            g = MagicMock()
            g.id = gid
            guids.append(g)
        item.guids = guids
        return item

    def test_extracts_tmdb_id(self):
        client = self._make_client()
        item = self._make_item_with_guids(["tmdb://12345"])
        tmdb_id, imdb_id = client._extract_external_ids(item)
        self.assertEqual(tmdb_id, 12345)
        self.assertIsNone(imdb_id)

    def test_extracts_imdb_id(self):
        client = self._make_client()
        item = self._make_item_with_guids(["imdb://tt1234567"])
        tmdb_id, imdb_id = client._extract_external_ids(item)
        self.assertIsNone(tmdb_id)
        self.assertEqual(imdb_id, "tt1234567")

    def test_extracts_both_ids(self):
        client = self._make_client()
        item = self._make_item_with_guids(["tmdb://999", "imdb://tt0000001"])
        tmdb_id, imdb_id = client._extract_external_ids(item)
        self.assertEqual(tmdb_id, 999)
        self.assertEqual(imdb_id, "tt0000001")

    def test_no_guids_returns_none(self):
        client = self._make_client()
        item = MagicMock()
        item.guids = []
        tmdb_id, imdb_id = client._extract_external_ids(item)
        self.assertIsNone(tmdb_id)
        self.assertIsNone(imdb_id)

    def test_missing_guids_attr_returns_none(self):
        client = self._make_client()
        item = MagicMock(spec=[])  # No attributes
        tmdb_id, imdb_id = client._extract_external_ids(item)
        self.assertIsNone(tmdb_id)
        self.assertIsNone(imdb_id)

    def test_invalid_tmdb_id_skipped(self):
        client = self._make_client()
        item = self._make_item_with_guids(["tmdb://not-a-number"])
        tmdb_id, imdb_id = client._extract_external_ids(item)
        self.assertIsNone(tmdb_id)

    def test_ignores_unknown_guid_prefix(self):
        client = self._make_client()
        item = self._make_item_with_guids(["tvdb://12345"])
        tmdb_id, imdb_id = client._extract_external_ids(item)
        self.assertIsNone(tmdb_id)
        self.assertIsNone(imdb_id)


class TestConvertToCachedMedia(unittest.TestCase):
    def _make_client(self):
        from cogs.plex.plex_client import PlexClientWrapper

        return PlexClientWrapper("http://plex:32400", "tok")

    def _make_plex_item(self, **overrides):
        item = MagicMock()
        item.type = overrides.get("type", "movie")
        item.ratingKey = overrides.get("ratingKey", 123)
        item.title = overrides.get("title", "Test Movie")
        item.year = overrides.get("year", 2024)
        item.thumb = overrides.get("thumb", "/thumb/123")
        item.summary = overrides.get("summary", "A test movie")
        item.rating = overrides.get("rating", 8.5)
        item.duration = overrides.get("duration", 7200000)
        item.addedAt = overrides.get("addedAt")
        item.guids = overrides.get("guids", [])
        return item

    def test_converts_movie(self):
        client = self._make_client()
        item = self._make_plex_item(type="movie", title="Inception", year=2010)
        result = client._convert_to_cached_media(item, "Movies")
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Inception")
        self.assertEqual(result.year, 2010)
        self.assertEqual(result.media_type, MediaType.MOVIE)
        self.assertEqual(result.library, "Movies")

    def test_converts_show_with_counts(self):
        client = self._make_client()
        item = self._make_plex_item(type="show", title="Breaking Bad")
        item.leafCount = 62
        item.childCount = 5
        result = client._convert_to_cached_media(item, "TV Shows")
        self.assertIsNotNone(result)
        self.assertEqual(result.media_type, MediaType.SHOW)
        self.assertEqual(result.episode_count, 62)
        self.assertEqual(result.season_count, 5)

    def test_movie_has_no_episode_count(self):
        client = self._make_client()
        item = self._make_plex_item(type="movie")
        result = client._convert_to_cached_media(item, "Movies")
        self.assertIsNone(result.episode_count)
        self.assertIsNone(result.season_count)

    def test_unknown_type_returns_none(self):
        client = self._make_client()
        item = self._make_plex_item(type="photo")
        result = client._convert_to_cached_media(item, "Photos")
        self.assertIsNone(result)

    def test_extracts_external_ids(self):
        client = self._make_client()
        guid = MagicMock()
        guid.id = "tmdb://550"
        item = self._make_plex_item(guids=[guid])
        result = client._convert_to_cached_media(item, "Movies")
        self.assertEqual(result.tmdb_id, 550)

    def test_exception_returns_none(self):
        client = self._make_client()
        item = MagicMock()
        item.type = "movie"
        # Force an error by making ratingKey raise
        type(item).ratingKey = PropertyMock(side_effect=RuntimeError("boom"))
        result = client._convert_to_cached_media(item, "Movies")
        self.assertIsNone(result)


class TestGetAllMedia(unittest.TestCase):
    def _make_client_with_server(self):
        from cogs.plex.plex_client import PlexClientWrapper

        client = PlexClientWrapper("http://plex:32400", "tok")
        client._server = MagicMock()
        return client

    def test_fetches_from_all_sections(self):
        client = self._make_client_with_server()

        movie_item = MagicMock()
        movie_item.type = "movie"
        movie_item.ratingKey = 1
        movie_item.title = "Movie"
        movie_item.year = 2024
        movie_item.thumb = None
        movie_item.summary = None
        movie_item.rating = None
        movie_item.duration = None
        movie_item.addedAt = None
        movie_item.guids = []

        section = MagicMock()
        section.type = "movie"
        section.title = "Movies"
        section.all.return_value = [movie_item]

        client._server.library.sections.return_value = [section]
        result = client.get_all_media()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Movie")

    def test_skips_unsupported_sections(self):
        client = self._make_client_with_server()

        photo_section = MagicMock()
        photo_section.type = "photo"
        photo_section.title = "Photos"

        client._server.library.sections.return_value = [photo_section]
        result = client.get_all_media()
        self.assertEqual(len(result), 0)

    def test_error_raises(self):
        client = self._make_client_with_server()
        client._server.library.sections.side_effect = RuntimeError("connection failed")
        with self.assertRaises(RuntimeError):
            client.get_all_media()


class TestSearch(unittest.TestCase):
    def _make_client_with_server(self):
        from cogs.plex.plex_client import PlexClientWrapper

        client = PlexClientWrapper("http://plex:32400", "tok")
        client._server = MagicMock()
        return client

    def test_returns_matching_results(self):
        client = self._make_client_with_server()

        item = MagicMock()
        item.type = "movie"
        item.ratingKey = 1
        item.title = "Inception"
        item.year = 2010
        item.thumb = None
        item.summary = None
        item.rating = None
        item.duration = None
        item.addedAt = None
        item.guids = []
        item.librarySectionTitle = "Movies"

        client._server.search.return_value = [item]
        result = client.search("inception")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Inception")

    def test_filters_non_matching_types(self):
        client = self._make_client_with_server()

        episode_item = MagicMock()
        episode_item.type = "episode"  # Not in the filter list

        client._server.search.return_value = [episode_item]
        result = client.search("test")
        self.assertEqual(len(result), 0)

    def test_error_returns_empty(self):
        client = self._make_client_with_server()
        client._server.search.side_effect = RuntimeError("fail")
        result = client.search("test")
        self.assertEqual(result, [])


class TestGetItemByKey(unittest.TestCase):
    def _make_client_with_server(self):
        from cogs.plex.plex_client import PlexClientWrapper

        client = PlexClientWrapper("http://plex:32400", "tok")
        client._server = MagicMock()
        return client

    def test_returns_item(self):
        client = self._make_client_with_server()

        item = MagicMock()
        item.type = "movie"
        item.ratingKey = 42
        item.title = "Found Movie"
        item.year = 2020
        item.thumb = None
        item.summary = None
        item.rating = None
        item.duration = None
        item.addedAt = None
        item.guids = []
        item.librarySectionTitle = "Movies"

        client._server.fetchItem.return_value = item
        result = client.get_item_by_key("42")
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Found Movie")
        client._server.fetchItem.assert_called_once_with(42)

    def test_not_found_returns_none(self):
        from plexapi.exceptions import NotFound

        client = self._make_client_with_server()
        client._server.fetchItem.side_effect = NotFound("not found")
        result = client.get_item_by_key("999")
        self.assertIsNone(result)

    def test_error_returns_none(self):
        client = self._make_client_with_server()
        client._server.fetchItem.side_effect = RuntimeError("fail")
        result = client.get_item_by_key("1")
        self.assertIsNone(result)


class TestGetActiveStreams(unittest.TestCase):
    def _make_client_with_server(self):
        from cogs.plex.plex_client import PlexClientWrapper

        client = PlexClientWrapper("http://plex:32400", "tok")
        client._server = MagicMock()
        return client

    def _make_session(self, **overrides):
        session = MagicMock()
        session.sessionKey = overrides.get("sessionKey", 1)
        session.title = overrides.get("title", "Test Movie")
        session.type = overrides.get("type", "movie")
        session.year = overrides.get("year", 2024)
        session.thumb = overrides.get("thumb", "/thumb/1")
        session.viewOffset = overrides.get("viewOffset", 3600000)
        session.duration = overrides.get("duration", 7200000)
        session.transcodeSessions = overrides.get("transcodeSessions", [])

        player = MagicMock()
        player.title = overrides.get("player_title", "Chrome")
        player.device = overrides.get("player_device", "Linux")
        player.state = overrides.get("player_state", "playing")
        session.players = [player]

        media = MagicMock()
        media.videoResolution = overrides.get("videoResolution", "1080")
        session.media = [media]

        return session

    def test_returns_active_streams(self):
        client = self._make_client_with_server()
        session = self._make_session(title="Inception", year=2010)
        client._server.sessions.return_value = [session]

        result = client.get_active_streams()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].media_title, "Inception")
        self.assertEqual(result[0].state, "playing")

    def test_episode_title_formatting(self):
        client = self._make_client_with_server()
        session = self._make_session(type="episode", title="Pilot")
        session.grandparentTitle = "Breaking Bad"
        session.parentIndex = 1
        session.index = 1
        client._server.sessions.return_value = [session]

        result = client.get_active_streams()
        self.assertEqual(result[0].media_title, "Breaking Bad - S01E01 - Pilot")

    def test_episode_without_season_episode_numbers(self):
        client = self._make_client_with_server()
        session = self._make_session(type="episode", title="Pilot")
        session.grandparentTitle = "Some Show"
        session.parentIndex = None
        session.index = None
        client._server.sessions.return_value = [session]

        result = client.get_active_streams()
        self.assertEqual(result[0].media_title, "Some Show - Pilot")

    def test_transcode_session(self):
        client = self._make_client_with_server()
        transcode = MagicMock()
        transcode.videoDecision = "transcode"
        session = self._make_session(transcodeSessions=[transcode])
        client._server.sessions.return_value = [session]

        result = client.get_active_streams()
        self.assertEqual(result[0].transcode_decision, "Transcode")

    def test_direct_play(self):
        client = self._make_client_with_server()
        session = self._make_session()
        client._server.sessions.return_value = [session]

        result = client.get_active_streams()
        self.assertEqual(result[0].transcode_decision, "Direct Play")

    def test_progress_calculation(self):
        client = self._make_client_with_server()
        session = self._make_session(viewOffset=3600000, duration=7200000)
        client._server.sessions.return_value = [session]

        result = client.get_active_streams()
        self.assertAlmostEqual(result[0].progress_percent, 50.0)

    def test_resolution_formatting_no_duplicate_p(self):
        client = self._make_client_with_server()
        session = self._make_session(videoResolution="1080p")
        client._server.sessions.return_value = [session]

        result = client.get_active_streams()
        self.assertEqual(result[0].quality, "1080p")  # Not "1080pp"

    def test_empty_sessions(self):
        client = self._make_client_with_server()
        client._server.sessions.return_value = []
        result = client.get_active_streams()
        self.assertEqual(result, [])

    def test_error_returns_empty(self):
        client = self._make_client_with_server()
        client._server.sessions.side_effect = RuntimeError("fail")
        result = client.get_active_streams()
        self.assertEqual(result, [])


class TestGetRecentlyAdded(unittest.TestCase):
    def _make_client_with_server(self):
        from cogs.plex.plex_client import PlexClientWrapper

        client = PlexClientWrapper("http://plex:32400", "tok")
        client._server = MagicMock()
        return client

    def _make_item(self, title="Test"):
        item = MagicMock()
        item.type = "movie"
        item.ratingKey = 1
        item.title = title
        item.year = 2024
        item.thumb = None
        item.summary = None
        item.rating = None
        item.duration = None
        item.addedAt = None
        item.guids = []
        item.librarySectionTitle = "Movies"
        return item

    def test_specific_library(self):
        client = self._make_client_with_server()
        section = MagicMock()
        section.title = "Movies"
        section.recentlyAdded.return_value = [self._make_item("New Movie")]
        client._server.library.sections.return_value = [section]

        result = client.get_recently_added(library="Movies", limit=5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "New Movie")
        section.recentlyAdded.assert_called_once_with(maxresults=5)

    def test_all_libraries(self):
        client = self._make_client_with_server()
        items = [self._make_item(f"Item {i}") for i in range(3)]
        client._server.library.recentlyAdded.return_value = items

        result = client.get_recently_added(limit=3)
        self.assertEqual(len(result), 3)

    def test_library_name_case_insensitive(self):
        client = self._make_client_with_server()
        section = MagicMock()
        section.title = "Movies"
        section.recentlyAdded.return_value = [self._make_item()]
        client._server.library.sections.return_value = [section]

        result = client.get_recently_added(library="movies")
        self.assertEqual(len(result), 1)

    def test_error_returns_empty(self):
        client = self._make_client_with_server()
        client._server.library.sections.side_effect = RuntimeError("fail")
        result = client.get_recently_added(library="Movies")
        self.assertEqual(result, [])


class TestGetLibraries(unittest.TestCase):
    def _make_client_with_server(self):
        from cogs.plex.plex_client import PlexClientWrapper

        client = PlexClientWrapper("http://plex:32400", "tok")
        client._server = MagicMock()
        return client

    def test_returns_library_names(self):
        client = self._make_client_with_server()
        s1, s2 = MagicMock(), MagicMock()
        s1.title = "Movies"
        s2.title = "TV Shows"
        client._server.library.sections.return_value = [s1, s2]

        result = client.get_libraries()
        self.assertEqual(result, ["Movies", "TV Shows"])

    def test_error_returns_empty(self):
        client = self._make_client_with_server()
        client._server.library.sections.side_effect = RuntimeError("fail")
        result = client.get_libraries()
        self.assertEqual(result, [])


class TestGetAvailableClients(unittest.TestCase):
    def _make_client_with_server(self):
        from cogs.plex.plex_client import PlexClientWrapper

        client = PlexClientWrapper("http://plex:32400", "tok")
        client._server = MagicMock()
        return client

    def test_returns_clients(self):
        client = self._make_client_with_server()
        plex_client_mock = MagicMock()
        plex_client_mock.machineIdentifier = "abc123"
        plex_client_mock.title = "Living Room TV"
        plex_client_mock.device = "Chromecast"
        plex_client_mock.platform = "Android"
        plex_client_mock.product = "Plex for Android"
        plex_client_mock.state = "idle"
        client._server.clients.return_value = [plex_client_mock]

        result = client.get_available_clients()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Living Room TV")
        self.assertEqual(result[0].machine_identifier, "abc123")
        self.assertIsInstance(result[0], PlexClient)

    def test_error_returns_empty(self):
        client = self._make_client_with_server()
        client._server.clients.side_effect = RuntimeError("fail")
        result = client.get_available_clients()
        self.assertEqual(result, [])


class TestGenerateWatchTogetherLink(unittest.TestCase):
    def _make_client_with_server(self):
        from cogs.plex.plex_client import PlexClientWrapper

        client = PlexClientWrapper("http://plex:32400", "tok")
        client._server = MagicMock()
        return client

    def test_generates_link(self):
        client = self._make_client_with_server()
        client._server.fetchItem.return_value = MagicMock()
        client._server.machineIdentifier = "server123"

        result = client.generate_watch_together_link("42")
        self.assertIn("server123", result)
        self.assertIn("42", result)
        self.assertIn("app.plex.tv", result)

    def test_error_returns_none(self):
        client = self._make_client_with_server()
        client._server.fetchItem.side_effect = RuntimeError("fail")
        result = client.generate_watch_together_link("42")
        self.assertIsNone(result)


class TestGetServerInfo(unittest.TestCase):
    def _make_client_with_server(self):
        from cogs.plex.plex_client import PlexClientWrapper

        client = PlexClientWrapper("http://plex:32400", "tok")
        client._server = MagicMock()
        return client

    def test_returns_info(self):
        client = self._make_client_with_server()
        client._server.friendlyName = "My Plex"
        client._server.version = "1.32.0"
        client._server.platform = "Linux"
        client._server.transcodeSessions.return_value = [MagicMock()]
        client._server.sessions.return_value = [MagicMock(), MagicMock()]

        result = client.get_server_info()
        self.assertEqual(result["name"], "My Plex")
        self.assertEqual(result["version"], "1.32.0")
        self.assertEqual(result["platform"], "Linux")
        self.assertEqual(result["transcodes"], 1)
        self.assertEqual(result["streams"], 2)

    def test_error_returns_empty_dict(self):
        client = self._make_client_with_server()
        client._server.transcodeSessions.side_effect = RuntimeError("fail")
        result = client.get_server_info()
        self.assertEqual(result, {})


class TestGetLibraryForItem(unittest.TestCase):
    def _make_client(self):
        from cogs.plex.plex_client import PlexClientWrapper

        return PlexClientWrapper("http://plex:32400", "tok")

    def test_returns_library_section_title(self):
        client = self._make_client()
        item = MagicMock()
        item.librarySectionTitle = "Movies"
        self.assertEqual(client._get_library_for_item(item), "Movies")

    def test_returns_unknown_when_missing(self):
        client = self._make_client()
        item = MagicMock(spec=[])  # No attributes
        self.assertEqual(client._get_library_for_item(item), "Unknown")


if __name__ == "__main__":
    unittest.main()
