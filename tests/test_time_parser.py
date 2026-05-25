import pytest
from stream_fetch.time_parser import TimeParser
from stream_fetch.models import DownloadConfig


def test_parse_seconds():
    assert TimeParser.parse("90") == 90.0
    assert TimeParser.parse("90.5") == 90.5


def test_parse_mm_ss():
    assert TimeParser.parse("1:30") == 90.0
    assert TimeParser.parse("30:00") == 1800.0


def test_parse_hh_mm_ss():
    assert TimeParser.parse("1:30:00") == 5400.0
    assert TimeParser.parse("00:01:30") == 90.0


def test_parse_invalid():
    with pytest.raises(ValueError, match="Invalid time"):
        TimeParser.parse("abc")


def test_validate_resolves_duration():
    cfg = DownloadConfig(url="x", start_sec=90.0, end_sec=None)
    TimeParser.validate(cfg, duration=60.0)
    assert cfg.end_sec == 150.0


def test_validate_end_and_duration_conflict():
    cfg = DownloadConfig(url="x", start_sec=90.0, end_sec=120.0)
    with pytest.raises(ValueError, match="Cannot specify both"):
        TimeParser.validate(cfg, duration=60.0)


def test_validate_duration_without_start():
    cfg = DownloadConfig(url="x")
    with pytest.raises(ValueError, match="--duration requires --start"):
        TimeParser.validate(cfg, duration=60.0)


def test_validate_end_before_start():
    cfg = DownloadConfig(url="x", start_sec=120.0, end_sec=60.0)
    with pytest.raises(ValueError, match="end time must be after start"):
        TimeParser.validate(cfg, duration=None)
