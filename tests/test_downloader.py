import pytest
from stream_fetch.downloader import SegmentDownloader
from stream_fetch.models import DownloadConfig, Segment


def _make_segments(durations: list[float]) -> list[Segment]:
    return [
        Segment(url=f"http://x/{i}.ts", duration=d, sequence_index=i)
        for i, d in enumerate(durations)
    ]


def test_filter_no_range():
    cfg = DownloadConfig(url="x")
    segs = _make_segments([6.0, 6.0, 6.0])
    dl = SegmentDownloader(cfg)
    filtered, trim_start, trim_end = dl.filter_segments(segs)
    assert filtered == segs
    assert trim_start is None
    assert trim_end is None


def test_filter_middle_range():
    # segments: 0-6, 6-12, 12-18, 18-24
    cfg = DownloadConfig(url="x", start_sec=7.0, end_sec=20.0)
    segs = _make_segments([6.0, 6.0, 6.0, 6.0])
    dl = SegmentDownloader(cfg)
    filtered, trim_start, trim_end = dl.filter_segments(segs)
    # seg1 (6-12) and seg2 (12-18) and seg3 (18-24) are needed
    assert len(filtered) == 3
    assert filtered[0].sequence_index == 1
    assert trim_start == pytest.approx(1.0)   # 7 - 6
    assert trim_end == pytest.approx(14.0)    # 20 - 6


def test_filter_exact_boundary():
    # start aligns exactly with segment boundary
    cfg = DownloadConfig(url="x", start_sec=6.0, end_sec=12.0)
    segs = _make_segments([6.0, 6.0, 6.0])
    dl = SegmentDownloader(cfg)
    filtered, trim_start, trim_end = dl.filter_segments(segs)
    assert len(filtered) == 1
    assert filtered[0].sequence_index == 1
    assert trim_start == pytest.approx(0.0)
    assert trim_end == pytest.approx(6.0)
