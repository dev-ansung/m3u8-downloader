from __future__ import annotations
import shutil
import subprocess
from pathlib import Path


class FfmpegManager:
    @staticmethod
    def check() -> None:
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "ffmpeg not found. Install it: https://ffmpeg.org/download.html"
            )

    @staticmethod
    def merge(
        segment_paths: list[Path],
        trim_start: float | None,
        trim_end: float | None,
        output_path: Path,
        tmp_dir: Path,
    ) -> None:
        concat_path = tmp_dir / "concat.ts"
        with concat_path.open("wb") as out:
            for path in segment_paths:
                out.write(path.read_bytes())

        cmd = ["ffmpeg", "-y", "-i", str(concat_path)]
        if trim_start is not None:
            cmd += ["-ss", str(trim_start)]
        if trim_end is not None:
            cmd += ["-to", str(trim_end)]
        cmd += ["-c", "copy", str(output_path)]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

        concat_path.unlink(missing_ok=True)
        for path in segment_paths:
            path.unlink(missing_ok=True)
