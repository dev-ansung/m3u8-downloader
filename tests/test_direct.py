import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from stream_fetch.direct import DirectDownloader
from stream_fetch.models import DownloadConfig
from stream_fetch.cli import _is_hls


# --- _is_hls ---

def test_is_hls_detects_m3u8():
    assert _is_hls("https://example.com/video.m3u8") is True
    assert _is_hls("https://example.com/playlist.M3U8") is True
    assert _is_hls("https://example.com/stream.m3u") is True


def test_is_hls_rejects_direct():
    assert _is_hls("https://example.com/video.mp4") is False
    assert _is_hls("https://example.com/clip.mov") is False
    assert _is_hls("https://example.com/stream") is False


# --- DirectDownloader ---

def _cfg(url="https://example.com/video.mp4", **kwargs):
    return DownloadConfig(url=url, **kwargs)


def test_full_download_no_range(tmp_path):
    out = tmp_path / "out.mp4"
    cfg = _cfg()
    dl = DirectDownloader(cfg)

    head_resp = MagicMock()
    head_resp.headers = {"Accept-Ranges": "none"}

    get_resp = MagicMock()
    get_resp.headers = {"Content-Length": "8"}
    get_resp.iter_content.return_value = [b"fakefake"]
    get_resp.raise_for_status = MagicMock()

    with patch.object(dl._session, "head", return_value=head_resp), \
         patch.object(dl._session, "get", return_value=get_resp):
        dl.download(out)

    assert out.read_bytes() == b"fakefake"


def test_trim_with_range_uses_ffmpeg_direct(tmp_path):
    out = tmp_path / "out.mp4"
    cfg = _cfg(start_sec=10.0, end_sec=30.0)
    dl = DirectDownloader(cfg)

    head_resp = MagicMock()
    head_resp.headers = {"Accept-Ranges": "bytes"}

    with patch.object(dl._session, "head", return_value=head_resp), \
         patch("stream_fetch.direct.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        dl.download(out)

    cmd = mock_run.call_args[0][0]
    assert "-ss" in cmd
    assert "10.0" in cmd
    assert "-t" in cmd
    assert "20.0" in cmd  # duration = end - start


def test_trim_without_range_warns_and_falls_back(tmp_path, capsys):
    out = tmp_path / "out.mp4"
    cfg = _cfg(start_sec=10.0, end_sec=30.0)
    dl = DirectDownloader(cfg)

    head_resp = MagicMock()
    head_resp.headers = {"Accept-Ranges": "none"}

    get_resp = MagicMock()
    get_resp.headers = {}
    get_resp.iter_content.return_value = [b"data"]
    get_resp.raise_for_status = MagicMock()

    with patch.object(dl._session, "head", return_value=head_resp), \
         patch.object(dl._session, "get", return_value=get_resp), \
         patch("stream_fetch.direct.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        dl.download(out)

    captured = capsys.readouterr()
    assert "does not support range requests" in captured.err
    assert mock_run.called
