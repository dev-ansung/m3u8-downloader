# stream-fetch

Download any video URL to MP4 — HLS streams or direct links — with optional time-range clipping.

```bash
uvx stream-fetch "https://example.com/video.m3u8" --start 30:00 --end 31:00
uvx stream-fetch "https://example.com/clip.mp4" --start 10 --end 40
```

**Why not just `ffmpeg -i <url> output.mp4`?**
ffmpeg downloads the entire stream before it can trim. For a 1-minute clip from a 2-hour HLS stream, `stream-fetch` downloads only the ~16 segments that cover that window — roughly 1% of the data. For direct video URLs it uses ffmpeg's native HTTP seek, so the server never sends what you don't need.

## Features

- **HLS streams** — parses m3u8 playlists, picks highest-bandwidth variant, downloads only the segments you need
- **Direct video URLs** — MP4, MOV, or any streamable format; uses HTTP range requests for partial fetches
- **Frame-accurate trimming** — segment-level filtering for HLS, ffmpeg `-ss`/`-t` seek for direct URLs; both avoid re-encoding
- **AES-128 encrypted streams** — auto-detects and decrypts `#EXT-X-KEY` protected HLS segments
- **Parallel downloads** — concurrent segment fetching for HLS (configurable worker count)
- **Custom headers** — pass `Referer`, `Cookie`, or anything else for CDN-gated streams
- **Zero install** — run directly with `uvx`, no global install needed

## Requirements

- Python ≥ 3.11
- [ffmpeg](https://ffmpeg.org/download.html) on your `PATH`

## Installation

Zero install — run directly:

```bash
uvx stream-fetch <url>
```

From a GitHub clone:

```bash
uvx --from git+https://github.com/dev-ansung/m3u8-downloader stream-fetch <url>
```

Install globally:

```bash
uv tool install stream-fetch
stream-fetch <url>
```

## Usage

```bash
# Full download → YYYYMMDD-HHMMSS.mp4
stream-fetch "https://example.com/video.m3u8"
stream-fetch "https://example.com/video.mp4"

# Clip by time range (HH:MM:SS or plain seconds)
stream-fetch <url> --start 30:00 --end 31:00
stream-fetch <url> --start 1800 --end 1860

# Start + duration
stream-fetch <url> --start 30:00 --duration 60

# Custom output filename
stream-fetch <url> --output clip.mp4

# Pass custom headers (repeatable)
stream-fetch <url> --header "Referer: https://example.com" --header "Cookie: session=abc"

# More parallel workers for HLS (default: 8)
stream-fetch <url> --workers 16
```

## How partial downloads work

### HLS streams (`.m3u8`)

HLS playlists list every segment with its duration (`#EXTINF`). `stream-fetch` accumulates those durations to find exactly which segments overlap `[--start, --end]` and downloads only those. After downloading, ffmpeg trims the edges with `-ss`/`-to` for frame accuracy — no re-encoding.

A 1-minute clip from a 90-minute stream with 4-second segments fetches ~16 segments instead of ~1350.

### Direct video URLs (`.mp4`, etc.)

`stream-fetch` checks whether the server supports HTTP range requests. If it does, ffmpeg is invoked with `-ss` and `-t` so the server only sends the bytes covering the requested window. If not, the full file is downloaded and trimmed locally (with a warning).

## CDN profiles

Some CDNs require specific `Referer` or `Origin` headers. Add a per-domain entry to `src/stream_fetch/site_profiles.py`:

```python
_PROFILES: dict[str, dict[str, str]] = {
    "cdn.example.com": {
        "Referer": "https://example.com/",
        "Origin": "https://example.com",
    },
}
```

Headers from `--header` flags always override profile defaults.

## Development

```bash
git clone https://github.com/dev-ansung/m3u8-downloader && cd m3u8-downloader
uv sync --dev
uv run stream-fetch --help
uv run pytest
```
