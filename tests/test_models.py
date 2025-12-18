import unittest
from datetime import datetime
import sys

sys.path.insert(0, "src")

# Import models directly to avoid loading discord
from cogs.plex.models import (
    CachedMedia,
    MediaType,
    ActiveStream,
    OverseerrSearchResult,
    RequestStatus,
)


class TestCachedMedia(unittest.TestCase):
    def test_display_title_with_year(self):
        media = CachedMedia(
            rating_key="123",
            title="Breaking Bad",
            year=2008,
            media_type=MediaType.SHOW,
            library="TV Shows",
        )
        self.assertEqual(media.display_title, "Breaking Bad (2008)")

    def test_display_title_without_year(self):
        media = CachedMedia(
            rating_key="123",
            title="Unknown Movie",
            year=None,
            media_type=MediaType.MOVIE,
            library="Movies",
        )
        self.assertEqual(media.display_title, "Unknown Movie")

    def test_type_emoji_movie(self):
        media = CachedMedia(
            rating_key="123",
            title="Test",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
        )
        self.assertEqual(media.type_emoji, "🎬")

    def test_type_emoji_show(self):
        media = CachedMedia(
            rating_key="123",
            title="Test",
            year=2024,
            media_type=MediaType.SHOW,
            library="TV",
        )
        self.assertEqual(media.type_emoji, "📺")

    def test_duration_formatted_hours_and_minutes(self):
        media = CachedMedia(
            rating_key="123",
            title="Test",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
            duration=7200000,  # 2 hours in ms
        )
        self.assertEqual(media.duration_formatted, "2h 0m")

    def test_duration_formatted_minutes_only(self):
        media = CachedMedia(
            rating_key="123",
            title="Test",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
            duration=1800000,  # 30 minutes in ms
        )
        self.assertEqual(media.duration_formatted, "30m")

    def test_duration_formatted_none(self):
        media = CachedMedia(
            rating_key="123",
            title="Test",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
            duration=None,
        )
        self.assertIsNone(media.duration_formatted)

    def test_tmdb_id_field(self):
        media = CachedMedia(
            rating_key="123",
            title="Test Movie",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
            tmdb_id=12345,
        )
        self.assertEqual(media.tmdb_id, 12345)

    def test_imdb_id_field(self):
        media = CachedMedia(
            rating_key="123",
            title="Test Movie",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
            imdb_id="tt1234567",
        )
        self.assertEqual(media.imdb_id, "tt1234567")

    def test_external_ids_default_none(self):
        media = CachedMedia(
            rating_key="123",
            title="Test",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
        )
        self.assertIsNone(media.tmdb_id)
        self.assertIsNone(media.imdb_id)


class TestActiveStream(unittest.TestCase):
    def test_progress_bar(self):
        stream = ActiveStream(
            session_key="1",
            media_title="Test",
            media_year=2024,
            media_type=MediaType.MOVIE,
            thumb=None,
            progress_percent=50.0,
            progress_time=3600000,
            duration=7200000,
            state="playing",
            quality="1080p",
            transcode_decision="Direct Play",
            player_name="Test Player",
            player_device="Test Device",
        )
        self.assertEqual(stream.progress_bar, "█████░░░░░")

    def test_progress_formatted(self):
        stream = ActiveStream(
            session_key="1",
            media_title="Test",
            media_year=2024,
            media_type=MediaType.MOVIE,
            thumb=None,
            progress_percent=50.0,
            progress_time=3661000,  # 1:01:01
            duration=7322000,  # 2:02:02
            state="playing",
            quality="1080p",
            transcode_decision="Direct Play",
            player_name=None,
            player_device=None,
        )
        self.assertEqual(stream.progress_formatted, "1:01:01 / 2:02:02")

    def test_state_emoji(self):
        stream = ActiveStream(
            session_key="1",
            media_title="Test",
            media_year=None,
            media_type=MediaType.MOVIE,
            thumb=None,
            progress_percent=0,
            progress_time=0,
            duration=1,
            state="paused",
            quality=None,
            transcode_decision=None,
            player_name=None,
            player_device=None,
        )
        self.assertEqual(stream.state_emoji, "⏸️")


class TestOverseerrSearchResult(unittest.TestCase):
    def test_poster_url(self):
        result = OverseerrSearchResult(
            media_type="movie",
            tmdb_id=123,
            title="Test Movie",
            year=2024,
            poster_path="/abc123.jpg",
            overview="Test overview",
        )
        self.assertEqual(
            result.poster_url, "https://image.tmdb.org/t/p/w500/abc123.jpg"
        )

    def test_poster_url_none(self):
        result = OverseerrSearchResult(
            media_type="movie",
            tmdb_id=123,
            title="Test Movie",
            year=2024,
            poster_path=None,
            overview="Test overview",
        )
        self.assertIsNone(result.poster_url)

    def test_type_emoji(self):
        movie = OverseerrSearchResult(
            media_type="movie",
            tmdb_id=1,
            title="Test",
            year=2024,
            poster_path=None,
            overview=None,
        )
        tv = OverseerrSearchResult(
            media_type="tv",
            tmdb_id=2,
            title="Test",
            year=2024,
            poster_path=None,
            overview=None,
        )
        self.assertEqual(movie.type_emoji, "🎬")
        self.assertEqual(tv.type_emoji, "📺")


if __name__ == "__main__":
    unittest.main()
