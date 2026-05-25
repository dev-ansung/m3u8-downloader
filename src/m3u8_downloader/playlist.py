from __future__ import annotations
import requests
import m3u8
from urllib.parse import urljoin

from m3u8_downloader.models import DownloadConfig, Segment
from m3u8_downloader.site_profiles import SiteProfiles


class PlaylistFetcher:
    def __init__(self, config: DownloadConfig) -> None:
        self._config = config
        self._session = requests.Session()
        self._session.headers.update(SiteProfiles.headers_for(config.url))
        self._session.headers.update(config.headers)

    def fetch(self) -> list[Segment]:
        playlist = self._load_playlist(self._config.url)
        if playlist.is_variant:
            best = max(playlist.playlists, key=lambda p: p.stream_info.bandwidth or 0)
            base = self._config.url
            variant_url = urljoin(base, best.uri)
            playlist = self._load_playlist(variant_url)
            base = variant_url
        else:
            base = self._config.url

        decrypt_key, iv_base = self._extract_key(playlist, base)
        segments: list[Segment] = []
        for i, seg in enumerate(playlist.segments):
            seg_url = urljoin(base, seg.uri)
            iv = iv_base if iv_base is not None else i.to_bytes(16, "big")
            segments.append(
                Segment(
                    url=seg_url,
                    duration=seg.duration,
                    sequence_index=i,
                    decrypt_key=decrypt_key,
                    iv=iv if decrypt_key else None,
                )
            )
        return segments

    def _load_playlist(self, url: str) -> m3u8.M3U8:
        resp = self._session.get(url, timeout=20)
        resp.raise_for_status()
        return m3u8.loads(resp.text, uri=url)

    def _extract_key(
        self, playlist: m3u8.M3U8, base_url: str
    ) -> tuple[bytes | None, bytes | None]:
        for key in playlist.keys:
            if key and key.method == "AES-128":
                key_url = urljoin(base_url, key.uri)
                resp = self._session.get(key_url, timeout=20)
                resp.raise_for_status()
                key_bytes = resp.content
                iv = bytes.fromhex(key.iv.lstrip("0x")) if key.iv else None
                return key_bytes, iv
        return None, None
