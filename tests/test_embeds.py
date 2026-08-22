from datetime import UTC, datetime, timedelta

from discord_plex.cogs.plex.embeds import (
    create_error_embed,
    create_media_embed,
    create_recently_added_embed,
    create_request_embed,
    create_server_stats_embed,
    create_stream_embed,
    create_success_embed,
    truncate,
)
from discord_plex.cogs.plex.models import (
    ActiveStream,
    CachedMedia,
    MediaType,
    OverseerrRequest,
    RequestStatus,
)


class TestTruncate:
    def test_short_text(self):
        text = "Hello"
        result = truncate(text, 100)
        assert result == "Hello"

    def test_long_text(self):
        text = "A" * 500
        result = truncate(text, 100)
        assert len(result) == 100
        assert result.endswith("...")

    def test_exact_length(self):
        text = "A" * 100
        result = truncate(text, 100)
        assert result == text


class TestCreateMediaEmbed:
    def test_basic_embed(self):
        media = CachedMedia(
            rating_key="123",
            title="Test Movie",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
            summary="A test movie summary.",
            rating=8.5,
            duration=7200000,
        )
        embed = create_media_embed(media, thumb_url=None)
        assert "Test Movie (2024)" in embed.title
        assert "A test movie summary" in embed.description

    def test_embed_with_thumbnail(self):
        media = CachedMedia(
            rating_key="123",
            title="Test",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
        )
        embed = create_media_embed(media, thumb_url="https://example.com/thumb.jpg")
        assert embed.thumbnail is not None


class TestCreateRecentlyAddedEmbed:
    def _media(self, added_at: datetime | None) -> CachedMedia:
        return CachedMedia(
            rating_key="123",
            title="Test Movie",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
            added_at=added_at,
        )

    def test_naive_added_at_renders_days_ago(self):
        media = [self._media(datetime.now() - timedelta(days=3))]
        embed = create_recently_added_embed(media, library="Movies")
        assert "Test Movie" in embed.description
        assert "3d ago" in embed.description

    def test_timezone_aware_added_at_does_not_raise(self):
        # plexapi 4.18.1 can return tz-aware datetimes; subtracting a naive
        # datetime.now() would raise TypeError. The embed must handle both.
        aware = datetime.now(UTC) - timedelta(days=3)
        embed = create_recently_added_embed([self._media(aware)], library="Movies")
        assert "Test Movie" in embed.description
        assert "3d ago" in embed.description

    def test_no_recent_media(self):
        embed = create_recently_added_embed([], library="Movies")
        assert "No recent additions" in embed.description

    def test_season_shows_its_show_title(self):
        # library.recentlyAdded() returns Season objects titled only "Season 1";
        # without the show name every TV addition looks identical.
        season = CachedMedia(
            rating_key="6374",
            title="Season 1",
            year=None,
            media_type=MediaType.SEASON,
            library="TV Shows",
            added_at=datetime.now(),
            parent_title="The X-Files",
        )
        embed = create_recently_added_embed([season], library="TV Shows")
        assert "The X-Files - Season 1" in embed.description

    def test_episode_shows_its_show_title(self):
        episode = CachedMedia(
            rating_key="99",
            title="Pilot",
            year=None,
            media_type=MediaType.EPISODE,
            library="TV Shows",
            added_at=datetime.now(),
            parent_title="Season 1",
            grandparent_title="The X-Files",
        )
        embed = create_recently_added_embed([episode], library="TV Shows")
        assert "The X-Files - Pilot" in embed.description

    def test_movie_title_is_not_prefixed(self):
        movie = self._media(datetime.now())
        movie.parent_title = "Some Collection"
        embed = create_recently_added_embed([movie], library="Movies")
        assert "**Test Movie**" in embed.description


class TestCreateServerStatsEmbed:
    def _stats(self, by_type: dict[str, int]) -> dict:
        return {
            "total_items": sum(by_type.values()),
            "by_type": by_type,
            "by_library": {"Movies": 1071, "TV Shows": 46},
            "last_refresh": None,
            "is_stale": False,
        }

    def test_type_counts_are_pluralised(self):
        embed = create_server_stats_embed({}, self._stats({"movie": 1071, "show": 84}))
        library_field = next(f for f in embed.fields if f.name == "Library")
        assert "Movies: 1071" in library_field.value
        assert "Shows: 84" in library_field.value

    def test_unknown_type_falls_back_to_naive_plural(self):
        embed = create_server_stats_embed({}, self._stats({"photo": 3}))
        library_field = next(f for f in embed.fields if f.name == "Library")
        assert "Photos: 3" in library_field.value


class TestCreateStreamEmbed:
    def test_stream_embed(self):
        stream = ActiveStream(
            session_key="1",
            media_title="Interstellar",
            media_year=2014,
            media_type=MediaType.MOVIE,
            thumb=None,
            progress_percent=50.0,
            progress_time=3600000,
            duration=7200000,
            state="playing",
            quality="1080p",
            transcode_decision="Direct Play",
            player_name="Living Room TV",
            player_device="Chromecast",
        )
        embed = create_stream_embed(stream)
        assert "Now Playing" in embed.title
        assert "Interstellar" in embed.description


class TestCreateRequestEmbed:
    def test_request_embed(self):
        request = OverseerrRequest(
            request_id=1,
            media_type="movie",
            tmdb_id=123,
            title="New Movie",
            year=2024,
            status=RequestStatus.PENDING,
            requested_by="testuser",
            requested_at=datetime.now(),
            poster_path="/poster.jpg",
            overview="A new movie to watch.",
        )
        embed = create_request_embed(request)
        assert "New Movie" in embed.title
        assert embed.thumbnail is not None


class TestCreateErrorEmbed:
    def test_error_embed(self):
        embed = create_error_embed("Something went wrong")
        assert "Error" in embed.title
        assert embed.description == "Something went wrong"


class TestCreateSuccessEmbed:
    def test_success_embed(self):
        embed = create_success_embed("Operation completed")
        assert "Success" in embed.title
        assert embed.description == "Operation completed"
