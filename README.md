# Help Scraper

CLI tool to turn documentation websites into Markdown files you can use as reference context for AI agents.

## Recommended for Advanced Installer User Guide

The user guide root page contains a table of contents with links to the full guide. Use TOC seeding to discover pages directly from that table of contents.

Target docs: <https://www.advancedinstaller.com/user-guide/>

```bash
python scraper.py \
  --url "https://www.advancedinstaller.com/user-guide/" \
  --seed-from-toc \
  --allowed-domain "www.advancedinstaller.com" \
  --url-prefix "https://www.advancedinstaller.com/user-guide/" \
  --max-pages 800 \
  --delay-seconds 0.2 \
  --output-dir output/advancedinstaller-user-guide
```

If you also want recursive traversal beyond TOC links, add `--crawl`.

## General usage

```bash
python scraper.py --url <page-url> [--url <page-url-2> ...] [options]
```

Options:
- `--url-file urls.txt`: read URLs from a file (one per line)
- `--seed-from-toc`: discover URLs from TOC containers on start page(s)
- `--toc-keyword keyword`: TOC detection keyword for id/class/aria-label (repeatable)
- `--crawl`: follow all discovered links
- `--allowed-domain <domain>`: only visit this domain (repeatable)
- `--url-prefix <prefix>`: only visit URLs with this prefix (repeatable)
- `--max-pages <n>`: stop after N successful pages
- `--delay-seconds <n>`: sleep between requests
- `--timeout <n>`: request timeout in seconds

## Output format

Each page is saved as:

```md
---
source_url: https://www.example.com/docs/page
scraped_at_utc: 2026-01-01T12:00:00+00:00
title: Example Page
---

# Example Page

...markdown content...
```

## Development

Run tests:

```bash
python -m unittest discover -s tests -p "test_*.py"
```
