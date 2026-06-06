from datetime import UTC, datetime, timedelta

from discord_plex.cogs.plex.embeds import (
    create_error_embed,
    create_media_embed,
    create_recently_added_embed,
    create_request_embed,
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
