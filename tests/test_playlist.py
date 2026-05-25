from stream_fetch.playlist import PlaylistFetcher
from stream_fetch.models import DownloadConfig


SIMPLE_M3U8 = """\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXTINF:6.0,
seg0.ts
#EXTINF:6.0,
seg1.ts
#EXTINF:6.0,
seg2.ts
#EXT-X-ENDLIST
"""


def test_fetch_returns_segments(requests_mock):
    requests_mock.get("http://example.com/video.m3u8", text=SIMPLE_M3U8)
    cfg = DownloadConfig(url="http://example.com/video.m3u8")
    fetcher = PlaylistFetcher(cfg)
    segments = fetcher.fetch()
    assert len(segments) == 3
    assert segments[0].url == "http://example.com/seg0.ts"
    assert segments[0].duration == 6.0
    assert segments[0].sequence_index == 0


def test_fetch_no_decrypt_key(requests_mock):
    requests_mock.get("http://example.com/video.m3u8", text=SIMPLE_M3U8)
    cfg = DownloadConfig(url="http://example.com/video.m3u8")
    fetcher = PlaylistFetcher(cfg)
    segments = fetcher.fetch()
    assert all(s.decrypt_key is None for s in segments)
