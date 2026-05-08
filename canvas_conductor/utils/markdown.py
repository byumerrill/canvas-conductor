"""Optional markdown-to-HTML converter used by extensions that publish Canvas pages.

Imports the `markdown` library lazily so the core CLI does not require it.
Install with: ``uv sync --extra markdown``.
"""
from __future__ import annotations


def markdown_to_html(text: str) -> str:
    """Convert markdown source to HTML suitable for Canvas page bodies."""
    try:
        import markdown as _md  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dep
        raise RuntimeError(
            "The `markdown` extra is not installed. Run: "
            "uv sync --extra markdown"
        ) from exc

    return _md.markdown(
        text,
        extensions=["fenced_code", "tables", "toc", "sane_lists"],
        output_format="html",
    )
