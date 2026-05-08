"""Link-header pagination utility.

The `CanvasClient` already inlines `Link` parsing; this module exposes the
same logic for use by extensions or scripts that build their own request
loops.
"""
from __future__ import annotations


def parse_link_header(header: str) -> dict[str, str]:
    """Return a `{rel: url}` mapping from a Canvas `Link` header value."""
    out: dict[str, str] = {}
    if not header:
        return out
    for part in header.split(","):
        section = part.strip()
        if not section.startswith("<"):
            continue
        url_part, *params = section.split(";")
        url = url_part.strip().lstrip("<").rstrip(">")
        for param in params:
            key, _, value = param.strip().partition("=")
            if key.strip() == "rel":
                out[value.strip().strip('"')] = url
    return out


def next_url(header: str) -> str | None:
    return parse_link_header(header).get("next")
