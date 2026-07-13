"""Safe URL construction for authenticated X API requests."""
from __future__ import annotations

import urllib.parse


API_BASE = "https://api.x.com/2/"


def build_x_api_url(path: str, query: str | None = None) -> str:
    """Return an X API v2 URL without allowing credentials to leave api.x.com."""
    parsed = urllib.parse.urlsplit(path)
    if parsed.scheme or parsed.netloc:
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.x.com"
            or parsed.port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or not parsed.path.startswith("/2/")
        ):
            raise ValueError("authenticated X API URLs must use https://api.x.com/2/")
        url = path
    else:
        url = API_BASE + path.lstrip("/")
    if query:
        separator = "&" if "?" in url else "?"
        url += separator + urllib.parse.urlencode({"query": query})
    return url
