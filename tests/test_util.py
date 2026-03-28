from util import chunk_text, format_duration, format_size, truncate_text


class TestChunkText:
    def test_short_text_returns_single_chunk(self):
        result = chunk_text("hello", chunk_size=10)
        assert result == ["hello"]

    def test_exact_limit_returns_single_chunk(self):
        text = "a" * 100
        result = chunk_text(text, chunk_size=100)
        assert result == [text]

    def test_splits_at_newline(self):
        text = "line one\nline two\nline three"
        result = chunk_text(text, chunk_size=18)
        assert result[0] == "line one\nline two"
        assert result[1] == "line three"

    def test_splits_at_space_when_no_good_newline(self):
        text = "word1 word2 word3 word4"
        result = chunk_text(text, chunk_size=12)
        assert result[0] == "word1 word2"
        assert result[1] == "word3 word4"

    def test_force_splits_when_no_whitespace(self):
        text = "a" * 20
        result = chunk_text(text, chunk_size=10)
        assert result == ["a" * 10, "a" * 10]

    def test_multiple_chunks(self):
        text = "aaa bbb ccc ddd eee fff"
        result = chunk_text(text, chunk_size=8)
        assert len(result) >= 3
        joined = " ".join(result)
        for word in ["aaa", "bbb", "ccc", "ddd", "eee", "fff"]:
            assert word in joined

    def test_empty_string(self):
        result = chunk_text("")
        assert result == [""]

    def test_default_chunk_size_is_4096(self):
        text = "a" * 4096
        result = chunk_text(text)
        assert len(result) == 1

        text = "a" * 4097
        result = chunk_text(text)
        assert len(result) == 2


class TestTruncateText:
    def test_short_text_unchanged(self):
        assert truncate_text("hello", 10) == "hello"

    def test_exact_length_unchanged(self):
        assert truncate_text("hello", 5) == "hello"

    def test_truncates_with_default_suffix(self):
        assert truncate_text("hello world", 8) == "hello..."

    def test_truncates_with_custom_suffix(self):
        assert truncate_text("hello world", 9, suffix="~") == "hello wo~"

    def test_empty_suffix(self):
        assert truncate_text("hello world", 5, suffix="") == "hello"


class TestFormatDuration:
    def test_hours_minutes_seconds(self):
        assert format_duration(9045000) == "2:30:45"

    def test_minutes_seconds_only(self):
        assert format_duration(330000) == "5:30"

    def test_zero(self):
        assert format_duration(0) == "0:00"

    def test_exactly_one_hour(self):
        assert format_duration(3600000) == "1:00:00"

    def test_pads_minutes_and_seconds(self):
        assert format_duration(3661000) == "1:01:01"

    def test_seconds_only(self):
        assert format_duration(5000) == "0:05"


class TestFormatSize:
    def test_bytes(self):
        assert format_size(500) == "500.0 B"

    def test_kilobytes(self):
        assert format_size(1024) == "1.0 KB"

    def test_megabytes(self):
        assert format_size(1048576) == "1.0 MB"

    def test_gigabytes(self):
        assert format_size(1073741824) == "1.0 GB"

    def test_terabytes(self):
        assert format_size(1099511627776) == "1.0 TB"

    def test_petabytes(self):
        assert format_size(1125899906842624) == "1.0 PB"

    def test_fractional(self):
        assert format_size(1610612736) == "1.5 GB"

    def test_zero(self):
        assert format_size(0) == "0.0 B"
