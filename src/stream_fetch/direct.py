from __future__ import annotations
import subprocess
import sys
from pathlib import Path

import requests
from tqdm import tqdm

from stream_fetch.models import DownloadConfig
from stream_fetch.site_profiles import SiteProfiles


class DirectDownloader:
    def __init__(self, config: DownloadConfig) -> None:
        self._config = config
        self._session = requests.Session()
        self._session.headers.update(SiteProfiles.headers_for(config.url))
        self._session.headers.update(config.headers)

    def download(self, output_path: Path) -> None:
        has_range = self._supports_range()
        has_trim = self._config.start_sec is not None or self._config.end_sec is not None

        if has_trim:
            if not has_range:
                print(
                    "Warning: server does not support range requests; "
                    "downloading full file then trimming.",
                    file=sys.stderr,
                )
                tmp = output_path.with_suffix(".tmp.mp4")
                self._stream_to_file(tmp)
                self._ffmpeg_trim(str(tmp), output_path)
                tmp.unlink(missing_ok=True)
            else:
                self._ffmpeg_direct(output_path)
        else:
            self._stream_to_file(output_path)

    def _supports_range(self) -> bool:
        try:
            resp = self._session.head(self._config.url, timeout=10, allow_redirects=True)
            return resp.headers.get("Accept-Ranges", "none").lower() != "none"
        except Exception:
            return False

    def _stream_to_file(self, output_path: Path) -> None:
        resp = self._session.get(self._config.url, stream=True, timeout=30)
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0)) or None
        with tqdm(total=total, unit="B", unit_scale=True, desc="Downloading") as bar:
            with output_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    bar.update(len(chunk))

    def _ffmpeg_direct(self, output_path: Path) -> None:
        cmd = ["ffmpeg", "-y"]
        if self._config.start_sec is not None:
            cmd += ["-ss", str(self._config.start_sec)]
        cmd += ["-i", self._config.url]
        if self._config.end_sec is not None:
            duration = self._config.end_sec - (self._config.start_sec or 0.0)
            cmd += ["-t", str(duration)]
        cmd += ["-c", "copy", str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    def _ffmpeg_trim(self, input_path: str, output_path: Path) -> None:
        cmd = ["ffmpeg", "-y", "-i", input_path]
        if self._config.start_sec is not None:
            cmd += ["-ss", str(self._config.start_sec)]
        if self._config.end_sec is not None:
            cmd += ["-to", str(self._config.end_sec)]
        cmd += ["-c", "copy", str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
