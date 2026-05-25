# m3u8dl

A fast, precise HLS stream downloader. Downloads an m3u8 playlist to MP4 with optional time-range clipping — only fetching the segments you actually need.

```bash
uvx m3u8dl "https://example.com/video.m3u8" --start 30:00 --end 31:00
```

## Features

- **Partial downloads** — specify a time window and only the relevant segments are downloaded. No wasted bandwidth.
- **Frame-accurate trimming** — segment filtering gets you close; ffmpeg `-ss`/`-to` trims the edges precisely.
- **AES-128 encrypted streams** — automatically detects and decrypts `#EXT-X-KEY` protected segments.
- **Variant playlist support** — picks the highest-bandwidth stream from a master playlist.
- **Parallel downloads** — segments are fetched concurrently with a configurable worker count.
- **Custom headers** — pass `Referer`, `Cookie`, or any other header for CDN-protected streams.
- **Site profiles** — built-in header presets for known CDNs (e.g. surrit.com → missav.ai).

## Requirements

- Python ≥ 3.11
- [ffmpeg](https://ffmpeg.org/download.html) on your `PATH`

## Installation

Run directly without installing:

```bash
uvx m3u8dl <url>
```

Or from a local clone / GitHub URL:

```bash
uvx --from git+https://github.com/your-username/m3u8-downloader m3u8dl <url>
```

Or install globally:

```bash
uv tool install m3u8dl
m3u8dl <url>
```

## Usage

```bash
# Full download → YYYYMMDD-HHMMSS.mp4
m3u8dl "https://example.com/video.m3u8"

# Partial download (HH:MM:SS or plain seconds, both work)
m3u8dl <url> --start 30:00 --end 31:00
m3u8dl <url> --start 1800 --end 1860

# Start + duration
m3u8dl <url> --start 30:00 --duration 60

# Custom output filename
m3u8dl <url> --output clip.mp4

# Pass custom headers (repeatable)
m3u8dl <url> --header "Referer: https://example.com" --header "Cookie: session=abc"

# Tune parallel workers (default: 8)
m3u8dl <url> --workers 16
```

## How partial downloads work

HLS streams are divided into fixed-duration segments (typically 4–10 seconds each). When you specify `--start` and `--end`:

1. **Segment filtering** — the playlist's `#EXTINF` durations are accumulated to find exactly which segments overlap the requested window. Only those segments are downloaded.
2. **Edge trimming** — the start offset within the first included segment and the end offset within the last are computed and passed to ffmpeg as `-ss` / `-to` during the final remux. This gives frame-accurate cuts without re-encoding.

For example, `--start 30:00 --end 31:00` on a stream with 4-second segments downloads ~16 segments instead of the full playlist, then trims to the exact second boundaries.

## Site profiles

Some CDNs require specific `Referer` or `Origin` headers. These are configured per-domain in `site_profiles.py` and applied automatically:

| CDN domain | Headers applied |
|------------|----------------|
| `surrit.com` | `Referer` and `Origin` set to the associated streaming site |

To add a new site, add an entry to `_PROFILES` in [src/m3u8_downloader/site_profiles.py](src/m3u8_downloader/site_profiles.py):

```python
_PROFILES: dict[str, dict[str, str]] = {
    "cdn.example.com": {
        "Referer": "https://example.com/",
        "Origin": "https://example.com",
    },
}
```

Headers passed via `--header` always take precedence over profile defaults.

## Development

```bash
git clone <repo> && cd m3u8-downloader
uv sync --dev
uv run m3u8dl --help
uv run pytest
```
