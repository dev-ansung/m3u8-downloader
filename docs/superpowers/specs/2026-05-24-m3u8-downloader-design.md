# m3u8-downloader Design Spec

**Date:** 2026-05-24  
**Status:** Draft

---

## Context

A command-line tool that downloads an HLS (m3u8) stream to a local MP4 file. The user provides a direct m3u8 URL; no page scraping or browser automation is needed. The core logic is adapted from [missav-downloader](https://github.com/gentlemanan/missav-downloader) but generalised: no site-specific scraping, optional custom HTTP headers, and support for partial downloads (start/end time) with both segment-level filtering and ffmpeg-level trimming for frame accuracy.

Usage:
```
# After uvx install (from PyPI):
uvx m3u8dl <m3u8-url>                              # full download → <timestamp>.mp4
uvx m3u8dl <url> --start 90 --end 180              # partial by seconds
uvx m3u8dl <url> --start 01:30 --end 03:00         # partial by HH:MM:SS
uvx m3u8dl <url> --start 90 --duration 60          # start + duration sugar
uvx m3u8dl <url> --output clip.mp4                 # custom output filename
uvx m3u8dl <url> --header "Referer: https://x.com" --header "Cookie: foo=bar"
uvx m3u8dl <url> --workers 8

# During development (from local checkout):
uv run m3u8dl <url>
```

---

## Architecture

### Package layout

```
m3u8-downloader/
├── pyproject.toml                  # name = "m3u8dl"; [project.scripts] m3u8dl = "m3u8_downloader.__main__:main"
├── src/
│   └── m3u8_downloader/
│       ├── __init__.py
│       ├── __main__.py             # thin entry: calls cli.main()
│       ├── cli.py                  # argparse, orchestrates the pipeline
│       ├── models.py               # Segment dataclass, DownloadConfig dataclass
│       ├── time_parser.py          # TimeParser class
│       ├── playlist.py             # PlaylistFetcher class
│       ├── downloader.py           # SegmentDownloader class
│       └── merger.py               # FfmpegManager class
└── tests/
```

### Module responsibilities

| Module | Class | Responsibility |
|--------|-------|---------------|
| `models.py` | `Segment` | Dataclass: url, duration, sequence_index, decrypt_key, iv |
| `models.py` | `DownloadConfig` | Dataclass: url, headers, start_sec, end_sec, output_path, workers |
| `time_parser.py` | `TimeParser` | Parse "90", "1:30", "01:30:00" → float seconds; validate ranges |
| `playlist.py` | `PlaylistFetcher` | Fetch m3u8 URL, resolve variants (picks highest bandwidth), parse segments with durations and AES key/IV, return `list[Segment]` |
| `downloader.py` | `SegmentDownloader` | Filter segments by time window, download with `ThreadPoolExecutor`, AES-128-CBC decrypt, tqdm progress, return ordered list of raw `.ts` bytes paths |
| `merger.py` | `FfmpegManager` | Verify ffmpeg is installed at startup; concatenate `.ts` files; apply `-ss`/`-to` trim for edge precision; remux to MP4; clean up temp files |
| `cli.py` | — | Parse args, build `DownloadConfig`, call pipeline in order, handle errors |

---

## Data Flow

```
cli.py
  │  parses args → DownloadConfig
  ▼
PlaylistFetcher.fetch(config)
  │  GET m3u8 → parse variants → parse segments+durations+keys
  │  returns list[Segment]
  ▼
SegmentDownloader.download(segments, config)
  │  filter segments to [start_sec, end_sec]
  │  ThreadPoolExecutor: GET each segment → AES decrypt if needed → write tmp file
  │  tqdm progress bar
  │  returns (list[tmp_paths], trim_start_offset, trim_end_offset)
  ▼
FfmpegManager.merge(tmp_paths, trim_start, trim_end, output_path)
  │  concat all .ts → single .ts
  │  ffmpeg -i concat.ts -ss trim_start -to trim_end -c copy output.mp4
  │  delete tmp files
  ▼
output.mp4
```

---

## Partial Download Logic

1. **Segment filtering:** Accumulate `#EXTINF` durations from the segment list. Include only segments whose time window overlaps `[start_sec, end_sec]`. This avoids downloading segments outside the requested range.

2. **Edge trimming offsets:** 
   - `trim_start_offset` = `start_sec - cumulative_duration_before_first_included_segment`
   - `trim_end_offset` = `end_sec - cumulative_duration_before_first_included_segment`
   - These are passed to ffmpeg as `-ss` and `-to` for frame-accurate edge cuts.

3. Full download (no `--start`/`--end`): no segment filtering, no ffmpeg trim flags.

---

## Time Parsing

`TimeParser.parse(value: str) -> float`:
- If value contains `:` → split on `:`, support `MM:SS` and `HH:MM:SS`
- Otherwise treat as float seconds
- Raises `ValueError` with a clear message on bad input

`TimeParser.validate(config: DownloadConfig)`:
- If both `--end` and `--duration` given → error
- If `--duration` given without `--start` → error  
- Resolve `--duration` → `end_sec = start_sec + duration`
- If `end_sec <= start_sec` → error

---

## HTTP / Headers

- Uses `requests.Session` with a shared header dict built from `--header` flags
- `--header` flag is repeatable; each value is `"Key: Value"` split on first `:`
- Default `User-Agent` set to a common browser string unless overridden
- 20-second timeout per segment request

---

## AES Decryption

- Handled inside `SegmentDownloader`, same approach as reference repo
- Uses `pycryptodome`: `AES.new(key, AES.MODE_CBC, iv)`
- Key fetched once from `#EXT-X-KEY` URI; IV from playlist or derived from segment sequence number
- If no `#EXT-X-KEY` present, segments are used as-is

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP client |
| `m3u8` | Playlist parsing |
| `pycryptodome` | AES-128-CBC decryption |
| `tqdm` | Download progress bar |
| ffmpeg | System requirement; checked at startup with `shutil.which("ffmpeg")` |

Python ≥ 3.11

---

## Output Filename

Default: `YYYYMMDD-HHMMSS.mp4` (local time at invocation). Override with `--output`.

---

## Error Handling

- Missing ffmpeg: print clear message and exit early (before any downloads)
- HTTP errors on playlist fetch: non-2xx → raise with URL and status code
- HTTP errors on segment fetch: retry once, then skip with warning (partial output still attempted)
- Invalid time args: caught in `TimeParser.validate`, printed as user error, no traceback

---

## Verification

```bash
# Dev: install locally and run
cd m3u8-downloader
uv run m3u8dl <public-test-m3u8-url>

# Partial download
uv run m3u8dl <url> --start 10 --end 30

# Custom output
uv run m3u8dl <url> --output test.mp4

# Header passing
uv run m3u8dl <url> --header "Referer: https://example.com"

# uvx (after publish to PyPI)
uvx m3u8dl <url>

# Verify output is valid MP4
ffprobe test.mp4

# Run tests
uv run pytest
```
