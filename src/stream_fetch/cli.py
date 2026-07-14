from __future__ import annotations
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from stream_fetch.models import DownloadConfig
from stream_fetch.time_parser import TimeParser
from stream_fetch.playlist import PlaylistFetcher
from stream_fetch.downloader import SegmentDownloader
from stream_fetch.merger import FfmpegManager
from stream_fetch.direct import DirectDownloader


def _parse_headers(header_list: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for h in header_list:
        key, _, value = h.partition(":")
        headers[key.strip()] = value.strip()
    return headers


def _is_hls(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".m3u8") or path.endswith(".m3u")


def _format_timestamp_for_filename(seconds: float) -> str:
    """Render seconds as MM_SS for use in a filename, e.g. 90.0 -> '1_30'.
    Matches video-processing's trim.py convention exactly."""
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes}_{secs:02d}"


def _default_output_path(start_sec: float | None, end_sec: float | None) -> Path:
    """YYYYMMDD-HHMMSS.mp4, or YYYYMMDD-HHMMSS.trim-{start}-{end}.mp4 when a
    time range is given."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if start_sec is None and end_sec is None:
        return Path(f"{timestamp}.mp4")
    start_label = _format_timestamp_for_filename(start_sec or 0.0)
    end_label = _format_timestamp_for_filename(end_sec) if end_sec is not None else "end"
    return Path(f"{timestamp}.trim-{start_label}-{end_label}.mp4")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="stream-fetch",
        description="Download HLS streams and direct video URLs to MP4",
    )
    parser.add_argument("url", help="Video URL (.m3u8 for HLS, or any direct video URL)")
    parser.add_argument("--start", "-s", metavar="TIME", help="Start time (seconds or HH:MM:SS)")
    parser.add_argument("--end", "-e", metavar="TIME", help="End time (seconds or HH:MM:SS)")
    parser.add_argument("--duration", "-d", metavar="TIME", help="Duration from --start (seconds or HH:MM:SS)")
    parser.add_argument(
        "--output", "-o", metavar="FILE",
        help="Output filename (default: YYYYMMDD-HHMMSS.trim-{start}-{end}.mp4, or without the .trim suffix if no time range given)",
    )
    parser.add_argument("--header", metavar="KEY:VALUE", action="append", default=[], dest="headers")
    parser.add_argument("--workers", type=int, default=8, metavar="N", help="Parallel download workers (default: 8, HLS only)")

    args = parser.parse_args()

    try:
        FfmpegManager.check()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        start_sec = TimeParser.parse(args.start) if args.start else None
        end_sec = TimeParser.parse(args.end) if args.end else None
        duration = TimeParser.parse(args.duration) if args.duration else None
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    config = DownloadConfig(
        url=args.url,
        headers=_parse_headers(args.headers),
        start_sec=start_sec,
        end_sec=end_sec,
        output_path=None,
        workers=args.workers,
    )

    try:
        TimeParser.validate(config, duration)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # validate() may resolve --duration into config.end_sec, so the default
    # filename (which embeds the time range) is computed after, not before.
    output_path = Path(args.output) if args.output else _default_output_path(
        config.start_sec, config.end_sec
    )
    config.output_path = output_path

    if _is_hls(args.url):
        _run_hls(config, output_path)
    else:
        _run_direct(config, output_path)


def _run_hls(config: DownloadConfig, output_path: Path) -> None:
    try:
        print(f"Fetching playlist: {config.url}")
        fetcher = PlaylistFetcher(config)
        segments = fetcher.fetch()
        print(f"Found {len(segments)} segments")
    except Exception as e:
        print(f"Error fetching playlist: {e}", file=sys.stderr)
        sys.exit(1)

    dl = SegmentDownloader(config)
    filtered, trim_start, trim_end = dl.filter_segments(segments)

    if not filtered:
        print("Error: no segments found in the requested time range", file=sys.stderr)
        sys.exit(1)

    if config.start_sec is not None:
        print(f"Downloading {len(filtered)} segments (time window: {config.start_sec}s – {config.end_sec}s)")
    else:
        print(f"Downloading {len(filtered)} segments")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        try:
            paths = dl.download(filtered, tmp_path)
        except Exception as e:
            print(f"Error during download: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"Merging to {output_path} ...")
        try:
            FfmpegManager.merge(paths, trim_start, trim_end, output_path, tmp_path)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    print(f"Done: {output_path}")


def _run_direct(config: DownloadConfig, output_path: Path) -> None:
    print(f"Downloading: {config.url}")
    try:
        DirectDownloader(config).download(output_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Done: {output_path}")
