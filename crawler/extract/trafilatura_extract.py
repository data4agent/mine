"""Trafilatura-based content extraction — SOTA article/wiki/blog extractor.

Trafilatura uses statistical heuristics (not deep learning) to identify
the main content area in HTML documents. It excels at:
- Wikipedia articles
- News sites
- Blog posts
- Academic pages

CPU-only, < 50ms per page, no GPU needed.
Falls back gracefully when Trafilatura is not installed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("crawler.extract.trafilatura")

try:
    import trafilatura
    from trafilatura.settings import use_config

    # Configure for maximum extraction quality
    _traf_config = use_config()
    _traf_config.set("DEFAULT", "MIN_OUTPUT_SIZE", "100")
    _traf_config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "100")
    _TRAFILATURA_AVAILABLE = True
except ImportError:
    trafilatura = None  # type: ignore[assignment]
    _traf_config = None
    _TRAFILATURA_AVAILABLE = False


@dataclass(frozen=True, slots=True)
class TrafilaturaResult:
    text: str
    html: str
    markdown: str
    title: str
    author: str
    date: str
    extractor: str


def extract_with_trafilatura(
    html: str,
    url: str,
) -> TrafilaturaResult | None:
    """Extract main content from HTML using Trafilatura.

    Returns None if Trafilatura is not installed or extraction fails.
    """
    if not _TRAFILATURA_AVAILABLE or not html:
        return None

    try:
        # Extract plain text — favor_recall for maximum content capture
        text = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            include_links=False,
            include_images=False,
            favor_recall=True,
            config=_traf_config,
        )
        if not text:
            return None

        # Extract metadata
        metadata = trafilatura.extract_metadata(html, default_url=url)
        title = ""
        author = ""
        date = ""
        if metadata:
            title = metadata.title or ""
            author = metadata.author or ""
            date = str(metadata.date or "")

        # Build markdown-like output from clean text
        lines = []
        if title:
            lines.append(f"# {title}")
            lines.append("")
        lines.append(text)
        markdown = "\n".join(lines)

        return TrafilaturaResult(
            text=text,
            html=xml_result or "",
            markdown=markdown,
            title=title,
            author=author,
            date=date,
            extractor="trafilatura",
        )

    except Exception as exc:
        log.warning("Trafilatura extraction failed for %s: %s", url, exc)
        return None
