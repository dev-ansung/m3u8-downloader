from __future__ import annotations
from urllib.parse import urlparse


_PROFILES: dict[str, dict[str, str]] = {
    "surrit.com": {
        "Referer": "https://missav.ai/",
        "Origin": "https://missav.ai",
    },
}

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class SiteProfiles:
    @staticmethod
    def headers_for(url: str) -> dict[str, str]:
        host = urlparse(url).hostname or ""
        base = {"User-Agent": _DEFAULT_UA}
        for domain, extra in _PROFILES.items():
            if host == domain or host.endswith("." + domain):
                base.update(extra)
                break
        return base
