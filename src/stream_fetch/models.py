from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Segment:
    url: str
    duration: float
    sequence_index: int
    decrypt_key: bytes | None = None
    iv: bytes | None = None


@dataclass
class DownloadConfig:
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    start_sec: float | None = None
    end_sec: float | None = None
    output_path: Path | None = None
    workers: int = 8
