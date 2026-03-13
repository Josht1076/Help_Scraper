#!/usr/bin/env python3
"""Scrape webpages into markdown files for AI-agent references."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import time
from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen

USER_AGENT = "HelpScraper/2.0 (+https://local.agent)"
BLOCK_TAGS = {"script", "style", "noscript", "svg"}


@dataclass
class ParsedPage:
    title: str
    markdown: str
    links: list[str]


class HTMLToMarkdownParser(HTMLParser):
    """Lightweight HTML -> Markdown parser for docs-like pages."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._buf: list[str] = []
        self._title_parts: list[str] = []
        self._in_title = False
        self._skip_depth = 0
        self._href_stack: list[str | None] = []
        self._list_stack: list[str] = []
        self._in_pre = False
        self._code_fence_open = False
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_map = dict(attrs)

        if tag in BLOCK_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        if tag == "title":
            self._in_title = True
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._newline(2)
            self._buf.append("#" * int(tag[1]) + " ")
            return
        if tag in {"p", "section", "article", "div"}:
            self._newline(2)
            return
        if tag in {"ul", "ol"}:
            self._list_stack.append(tag)
            self._newline(1)
            return
        if tag == "li":
            self._newline(1)
            depth = len(self._list_stack) - 1
            prefix = "  " * max(depth, 0)
            bullet = "1. " if self._list_stack and self._list_stack[-1] == "ol" else "- "
            self._buf.append(prefix + bullet)
            return
        if tag == "br":
            self._buf.append("\n")
            return
        if tag == "pre":
            self._newline(2)
            self._buf.append("```\n")
            self._in_pre = True
            self._code_fence_open = True
            return
        if tag == "code" and not self._in_pre:
            self._buf.append("`")
            return
        if tag == "a":
            href = attrs_map.get("href")
            self._href_stack.append(href)
            if href:
                self.links.append(href)
            self._buf.append("[")
            return
        if tag == "img":
            alt = (attrs_map.get("alt") or "image").strip()
            src = attrs_map.get("src") or ""
            if src:
                self.links.append(src)
            self._buf.append(f"![{alt}]({src})")

    def handle_endtag(self, tag):
        if tag in BLOCK_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return

        if tag == "title":
            self._in_title = False
            return
        if tag in {"ul", "ol"} and self._list_stack:
            self._list_stack.pop()
            self._newline(1)
            return
        if tag == "pre" and self._code_fence_open:
            self._buf.append("\n```\n")
            self._in_pre = False
            self._code_fence_open = False
            return
        if tag == "code" and not self._in_pre:
            self._buf.append("`")
            return
        if tag == "a":
            href = self._href_stack.pop() if self._href_stack else None
            if href:
                self._buf.append(f"]({href})")
            else:
                self._buf.append("]")

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_title:
            text = data.strip()
            if text:
                self._title_parts.append(text)
        if not data.strip():
            return
        text = html.unescape(data)
        if self._in_pre:
            self._buf.append(text)
        else:
            normalized = re.sub(r"\s+", " ", text).strip()
            if normalized:
                self._buf.append(normalized)

    def title(self) -> str:
        return " ".join(self._title_parts).strip() or "Untitled"

    def markdown(self) -> str:
        text = "".join(self._buf)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        return text.strip() + "\n"

    def _newline(self, n: int):
        if not self._buf:
            return
        current = "".join(self._buf)
        if current.endswith("\n" * n):
            return
        if current.endswith("\n"):
            self._buf.append("\n" * (n - 1))
        else:
            self._buf.append("\n" * n)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Turn webpages into markdown files for AI-agent references.")
    p.add_argument("--url", action="append", default=[], help="URL to scrape (repeatable)")
    p.add_argument("--url-file", help="File with one URL per line")
    p.add_argument("--output-dir", default="output", help="Directory for markdown output")
    p.add_argument("--max-pages", type=int, default=200, help="Max pages to scrape")
    p.add_argument("--delay-seconds", type=float, default=0.3, help="Delay between requests")
    p.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds")
    p.add_argument("--crawl", action="store_true", help="Follow links within allowed domains")
    p.add_argument(
        "--allowed-domain",
        action="append",
        default=[],
        help="Domain allowed for crawl (repeatable). Defaults to start URL domains.",
    )
    p.add_argument(
        "--url-prefix",
        action="append",
        default=[],
        help="Only save/crawl URLs starting with one of these prefixes (repeatable).",
    )
    p.add_argument(
        "--follow-next-selector",
        help="Compatibility flag from previous revision (no-op in this parser).",
    )
    return p.parse_args()


def read_start_urls(args: argparse.Namespace) -> list[str]:
    urls = list(args.url)
    if args.url_file:
        lines = Path(args.url_file).read_text(encoding="utf-8").splitlines()
        urls.extend(line.strip() for line in lines if line.strip() and not line.strip().startswith("#"))
    urls = [normalize_url(u) for u in urls if u.strip()]
    deduped = list(dict.fromkeys(urls))
    if not deduped:
        raise SystemExit("No URLs provided. Use --url and/or --url-file.")
    return deduped


def normalize_url(url: str) -> str:
    return urldefrag(url.strip())[0]


def slugify_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace(":", "-")
    path = parsed.path.strip("/") or "index"
    raw = f"{host}-{path}".replace("/", "-")
    if parsed.query:
        raw += "-" + parsed.query
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw).strip("-").lower()
    return slug[:180] or "page"


def fetch_html(url: str, timeout: float) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        enc = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(enc, errors="replace")


def parse_page(html_doc: str, base_url: str) -> ParsedPage:
    parser = HTMLToMarkdownParser()
    parser.feed(html_doc)
    links = [normalize_url(urljoin(base_url, href)) for href in parser.links if href]
    links = [u for u in links if urlparse(u).scheme in {"http", "https"}]
    return ParsedPage(title=parser.title(), markdown=parser.markdown(), links=list(dict.fromkeys(links)))


def should_visit(url: str, allowed_domains: set[str], prefixes: list[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if allowed_domains and parsed.netloc not in allowed_domains:
        return False
    if prefixes and not any(url.startswith(p) for p in prefixes):
        return False
    return True


def render_markdown(url: str, title: str, body: str) -> str:
    ts = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return (
        "---\n"
        f"source_url: {url}\n"
        f"scraped_at_utc: {ts}\n"
        f"title: {title}\n"
        "---\n\n"
        f"# {title}\n\n"
        f"{body.strip()}\n"
    )


def scrape(args: argparse.Namespace) -> int:
    start_urls = read_start_urls(args)
    allowed_domains = set(args.allowed_domain) if args.allowed_domain else {urlparse(u).netloc for u in start_urls}
    prefixes = args.url_prefix

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    queue: deque[str] = deque(start_urls)
    seen: set[str] = set()
    count = 0

    while queue and count < args.max_pages:
        url = queue.popleft()
        if url in seen or not should_visit(url, allowed_domains, prefixes):
            continue
        seen.add(url)

        print(f"[fetch] {url}")
        try:
            html_doc = fetch_html(url, args.timeout)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {url}: {exc}")
            continue

        page = parse_page(html_doc, url)
        output = out_dir / f"{slugify_url(url)}.md"
        output.write_text(render_markdown(url, page.title, page.markdown), encoding="utf-8")
        print(f"[saved] {output}")
        count += 1

        if args.crawl:
            for link in page.links:
                if link not in seen:
                    queue.append(link)

        if args.delay_seconds > 0:
            time.sleep(args.delay_seconds)

    print(f"[done] Scraped {count} page(s).")
    return count


def main() -> None:
    args = parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
