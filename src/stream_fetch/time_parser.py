from __future__ import annotations
from stream_fetch.models import DownloadConfig


class TimeParser:
    @staticmethod
    def parse(value: str) -> float:
        value = value.strip()
        if ":" in value:
            parts = value.split(":")
            if len(parts) == 2:
                minutes, seconds = parts
                return int(minutes) * 60 + float(seconds)
            elif len(parts) == 3:
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            raise ValueError(f"Invalid time format: '{value}'")
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"Invalid time '{value}': expected seconds or HH:MM:SS")

    @staticmethod
    def validate(config: DownloadConfig, duration: float | None) -> None:
        if duration is not None and config.end_sec is not None:
            raise ValueError("Cannot specify both --end and --duration")
        if duration is not None and config.start_sec is None:
            raise ValueError("--duration requires --start")
        if duration is not None:
            config.end_sec = (config.start_sec or 0.0) + duration
        if config.start_sec is not None and config.end_sec is not None:
            if config.end_sec <= config.start_sec:
                raise ValueError("end time must be after start time")
