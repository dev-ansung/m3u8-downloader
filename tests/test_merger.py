from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from stream_fetch.merger import FfmpegManager


def test_check_ffmpeg_raises_if_missing():
    with patch("stream_fetch.merger.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            FfmpegManager.check()


def test_check_ffmpeg_passes_if_present():
    with patch("stream_fetch.merger.shutil.which", return_value="/usr/bin/ffmpeg"):
        FfmpegManager.check()  # should not raise


def test_merge_calls_ffmpeg_without_trim(tmp_path):
    seg1 = tmp_path / "seg_000000.ts"
    seg1.write_bytes(b"fake")
    out = tmp_path / "out.mp4"

    with patch("stream_fetch.merger.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        FfmpegManager.merge(
            segment_paths=[seg1],
            trim_start=None,
            trim_end=None,
            output_path=out,
            tmp_dir=tmp_path,
        )
        cmd = mock_run.call_args[0][0]
        assert "-ss" not in cmd
        assert "-to" not in cmd
        assert str(out) in cmd


def test_merge_calls_ffmpeg_with_trim(tmp_path):
    seg1 = tmp_path / "seg_000000.ts"
    seg1.write_bytes(b"fake")
    out = tmp_path / "out.mp4"

    with patch("stream_fetch.merger.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        FfmpegManager.merge(
            segment_paths=[seg1],
            trim_start=1.0,
            trim_end=55.0,
            output_path=out,
            tmp_dir=tmp_path,
        )
        cmd = mock_run.call_args[0][0]
        assert "-ss" in cmd
        assert "1.0" in cmd
        assert "-to" in cmd
        assert "55.0" in cmd
