from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from Crypto.Cipher import AES
from tqdm import tqdm

from m3u8_downloader.models import DownloadConfig, Segment
from m3u8_downloader.site_profiles import SiteProfiles


class SegmentDownloader:
    def __init__(self, config: DownloadConfig) -> None:
        self._config = config
        self._session = requests.Session()
        self._session.headers.update(SiteProfiles.headers_for(config.url))
        self._session.headers.update(config.headers)

    def filter_segments(
        self, segments: list[Segment]
    ) -> tuple[list[Segment], float | None, float | None]:
        start = self._config.start_sec
        end = self._config.end_sec
        if start is None and end is None:
            return segments, None, None

        start = start or 0.0
        result: list[Segment] = []
        cumulative = 0.0
        first_seg_start: float | None = None

        for seg in segments:
            seg_end = cumulative + seg.duration
            if seg_end > start and cumulative < end:
                if first_seg_start is None:
                    first_seg_start = cumulative
                result.append(seg)
            cumulative += seg.duration

        if not result or first_seg_start is None:
            return [], None, None

        trim_start = start - first_seg_start
        trim_end = end - first_seg_start
        return result, trim_start, trim_end

    def download(
        self, segments: list[Segment], tmp_dir: Path
    ) -> list[Path]:
        paths: dict[int, Path] = {}

        def fetch_one(seg: Segment) -> tuple[int, Path | None]:
            for attempt in range(2):
                try:
                    resp = self._session.get(seg.url, timeout=20)
                    resp.raise_for_status()
                    data = resp.content
                    if seg.decrypt_key:
                        cipher = AES.new(seg.decrypt_key, AES.MODE_CBC, seg.iv)
                        data = cipher.decrypt(data)
                    out = tmp_dir / f"seg_{seg.sequence_index:06d}.ts"
                    out.write_bytes(data)
                    return seg.sequence_index, out
                except Exception:
                    if attempt == 1:
                        tqdm.write(f"Warning: failed to download {seg.url}, skipping")
            return seg.sequence_index, None

        with ThreadPoolExecutor(max_workers=self._config.workers) as pool:
            futures = {pool.submit(fetch_one, seg): seg for seg in segments}
            with tqdm(total=len(segments), unit="seg", desc="Downloading") as bar:
                for future in as_completed(futures):
                    idx, path = future.result()
                    if path:
                        paths[idx] = path
                    bar.update(1)

        return [paths[k] for k in sorted(paths)]
