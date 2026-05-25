from __future__ import annotations
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from m3u8_downloader.models import DownloadConfig
from m3u8_downloader.time_parser import TimeParser
from m3u8_downloader.playlist import PlaylistFetcher
from m3u8_downloader.downloader import SegmentDownloader
from m3u8_downloader.merger import FfmpegManager


def _parse_headers(header_list: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for h in header_list:
        key, _, value = h.partition(":")
        headers[key.strip()] = value.strip()
    return headers


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="m3u8dl",
        description="Download an HLS m3u8 stream to MP4",
    )
    parser.add_argument("url", help="m3u8 playlist URL")
    parser.add_argument("--start", metavar="TIME", help="Start time (seconds or HH:MM:SS)")
    parser.add_argument("--end", metavar="TIME", help="End time (seconds or HH:MM:SS)")
    parser.add_argument("--duration", metavar="TIME", help="Duration from --start (seconds or HH:MM:SS)")
    parser.add_argument("--output", "-o", metavar="FILE", help="Output filename (default: YYYYMMDD-HHMMSS.mp4)")
    parser.add_argument("--header", metavar="KEY:VALUE", action="append", default=[], dest="headers")
    parser.add_argument("--workers", type=int, default=8, metavar="N", help="Parallel download workers (default: 8)")

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

    output_path = Path(args.output) if args.output else Path(
        datetime.now().strftime("%Y%m%d-%H%M%S") + ".mp4"
    )

    config = DownloadConfig(
        url=args.url,
        headers=_parse_headers(args.headers),
        start_sec=start_sec,
        end_sec=end_sec,
        output_path=output_path,
        workers=args.workers,
    )

    try:
        TimeParser.validate(config, duration)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

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
