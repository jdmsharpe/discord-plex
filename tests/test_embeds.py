import unittest
from datetime import datetime

import sys

sys.path.insert(0, "src")

from cogs.plex.models import (
    CachedMedia,
    MediaType,
    ActiveStream,
    OverseerrRequest,
    RequestStatus,
)
from cogs.plex.embeds import (
    truncate,
    create_media_embed,
    create_search_results_embed,
    create_stream_embed,
    create_request_embed,
    create_error_embed,
    create_success_embed,
)


class TestTruncate(unittest.TestCase):
    def test_short_text(self):
        text = "Hello"
        result = truncate(text, 100)
        self.assertEqual(result, "Hello")

    def test_long_text(self):
        text = "A" * 500
        result = truncate(text, 100)
        self.assertEqual(len(result), 100)
        self.assertTrue(result.endswith("..."))

    def test_exact_length(self):
        text = "A" * 100
        result = truncate(text, 100)
        self.assertEqual(result, text)


class TestCreateMediaEmbed(unittest.TestCase):
    def test_basic_embed(self):
        media = CachedMedia(
            rating_key="123",
            title="Test Movie",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
            summary="A test movie summary.",
            rating=8.5,
            duration=7200000,  # 2 hours
        )
        embed = create_media_embed(media, thumb_url=None)

        self.assertIn("Test Movie (2024)", embed.title)
        self.assertIn("A test movie summary", embed.description)

    def test_embed_with_thumbnail(self):
        media = CachedMedia(
            rating_key="123",
            title="Test",
            year=2024,
            media_type=MediaType.MOVIE,
            library="Movies",
        )
        embed = create_media_embed(media, thumb_url="https://example.com/thumb.jpg")
        self.assertIsNotNone(embed.thumbnail)


class TestCreateStreamEmbed(unittest.TestCase):
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

        self.assertIn("Now Playing", embed.title)
        self.assertIn("Interstellar", embed.description)


class TestCreateRequestEmbed(unittest.TestCase):
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

        self.assertIn("New Movie", embed.title)
        self.assertIsNotNone(embed.thumbnail)


class TestCreateErrorEmbed(unittest.TestCase):
    def test_error_embed(self):
        embed = create_error_embed("Something went wrong")
        self.assertIn("Error", embed.title)
        self.assertEqual(embed.description, "Something went wrong")


class TestCreateSuccessEmbed(unittest.TestCase):
    def test_success_embed(self):
        embed = create_success_embed("Operation completed")
        self.assertIn("Success", embed.title)
        self.assertEqual(embed.description, "Operation completed")


if __name__ == "__main__":
    unittest.main()
