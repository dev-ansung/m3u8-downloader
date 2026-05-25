from m3u8_downloader.models import Segment, DownloadConfig


def test_segment_defaults():
    seg = Segment(url="http://example.com/0.ts", duration=6.0, sequence_index=0)
    assert seg.decrypt_key is None
    assert seg.iv is None


def test_download_config_defaults():
    cfg = DownloadConfig(url="http://example.com/video.m3u8")
    assert cfg.headers == {}
    assert cfg.start_sec is None
    assert cfg.end_sec is None
    assert cfg.workers == 8
