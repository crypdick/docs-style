#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = ["requests", "beautifulsoup4", "markdownify"]
# ///
"""crawl_to_markdown.py

Recursively crawl a website starting from a given base URL and export the main
content of each page to Markdown files. Only links that remain within the base
URL will be followed.

Usage:
    # Save each crawled page as individual Markdown files
    uv run crawl_to_markdown.py --base-url https://developers.google.com/style \
                                --output-dir ./out

    # Same as above, plus concatenate everything into a single file
    uv run crawl_to_markdown.py --base-url https://developers.google.com/style \
                                --output-dir ./out \
                                --combined-file all_pages.md

Dependencies are managed via the uv inline metadata at the top of this file.

The script detects an ``<article>``, ``<main>``, or fallback ``<body>`` tag to
extract content while ignoring sidebars and other page furniture.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as md

# Add root to sys.path to allow importing settings
sys.path.append(str(Path(__file__).resolve().parents[1]))

from settings import CRAWLER_HEADERS

# Type alias for stored page info: (url, title, saved_path)
PageInfo = tuple[str, str, Path]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


HEADERS = CRAWLER_HEADERS


def sanitize_path(url: str, base_netloc: str) -> Path:
    """Convert a URL path into a safe local file path with .md extension."""
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != base_netloc:
        raise ValueError("URL outside base domain")

    # Use path; ensure it ends with index if directory-like.
    path = parsed.path
    if path.endswith("/") or path == "":
        path = path + "index"
    out_path = Path(path.lstrip("/"))
    return out_path.with_suffix(".md")


def extract_main_content(soup: BeautifulSoup) -> Tag | None:
    """Return the tag that contains the main textual content."""
    for selector in ("article", "main", 'div[role="main"]'):
        tag = soup.select_one(selector)
        if tag:
            return tag
    return soup.body  # Fallback


def process_page(
    session: requests.Session,
    url: str,
    output_dir: Path,
    base_netloc: str,
) -> tuple[PageInfo | None, list[str]]:
    """
    Download and process a single URL.
    Returns (PageInfo, list_of_links_found).
    """
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(f"Skipping {url}: {exc}")
        return None, []

    soup = BeautifulSoup(resp.text, "html.parser")
    main_tag = extract_main_content(soup)
    if not main_tag:
        logger.info(f"No main content found for {url}")
        return None, []

    markdown = md(str(main_tag), heading_style="ATX")
    out_path = output_dir / sanitize_path(url, base_netloc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    title = soup.title.string.strip() if soup.title and soup.title.string else url
    logger.info(f"Saved {url} -> {out_path.relative_to(output_dir)}")

    links = []
    for a in soup.find_all("a", href=True):
        links.append(a["href"].strip())

    return (url, title, out_path), links


def crawl(base_url: str, output_dir: Path) -> list[PageInfo]:
    parsed_base = urlparse(base_url)
    base_netloc = parsed_base.netloc
    base_scheme = parsed_base.scheme
    base_path_prefix = parsed_base.path.rstrip("/") or "/"  # e.g., '/style'

    visited: set[str] = set()
    queue: deque[str] = deque([base_url])

    saved_pages: list[PageInfo] = []

    session = requests.Session()
    session.headers.update(HEADERS)

    while queue:
        url = queue.popleft()
        url = urldefrag(url).url  # Remove fragment

        # Skip URLs that are outside the base path prefix (e.g., '/style').
        parsed_current = urlparse(url)
        if parsed_current.netloc != base_netloc or not parsed_current.path.startswith(
            base_path_prefix
        ):
            continue

        if url in visited:
            continue
        visited.add(url)

        page_info, raw_links = process_page(session, url, output_dir, base_netloc)
        if page_info:
            saved_pages.append(page_info)

        for href in raw_links:
            if href.startswith(("mailto:", "javascript:")):
                continue
            next_url = urljoin(url, href)
            parsed_next = urlparse(next_url)
            if parsed_next.scheme not in {base_scheme, ""}:
                continue  # Different scheme (e.g., http vs https)
            if parsed_next.netloc != base_netloc:
                continue  # External domain
            if not parsed_next.path.startswith(base_path_prefix):
                continue  # Outside the base path
            queue.append(next_url)

    return saved_pages


def write_concatenated_markdown(pages: list[PageInfo], combined_path: Path) -> None:
    """Write all pages into a single Markdown file with delimiters."""
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    with combined_path.open("w", encoding="utf-8") as fout:
        for idx, (url, title, md_path) in enumerate(pages):
            if idx > 0:
                fout.write("\n\n---\n\n")
            fout.write(f"# {title}\n\n")
            fout.write(f"*Source: [{url}]({url})*\n\n")
            fout.write(md_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl a site and export pages to Markdown.")
    parser.add_argument("--base-url", required=True, help="Base URL to start crawling.")
    parser.add_argument(
        "--output-dir",
        default="site_markdown",
        help="Directory where Markdown files will be stored (default: %(default)s)",
    )
    parser.add_argument(
        "--combined-file",
        default=None,
        help=(
            "If provided, concatenates all pages into the specified Markdown file "
            "after crawling (path can be inside or outside output dir)."
        ),
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = crawl(args.base_url, output_dir)

    if args.combined_file:
        combined_path = Path(args.combined_file)
        write_concatenated_markdown(pages, combined_path)
        logger.info(f"Wrote concatenated markdown to {combined_path}")


if __name__ == "__main__":
    main()
