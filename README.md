# Help Scraper

CLI tool to turn documentation websites into Markdown files you can use as reference context for AI agents.

## What this version improves

- Better HTML → Markdown conversion (headings, lists, links, code blocks, images)
- Real crawling mode (`--crawl`) for scraping a full docs section
- Domain and URL-prefix guards so crawls stay scoped
- Frontmatter metadata for every generated Markdown file

## Quick start (Advanced Installer User Guide)

Target docs: <https://www.advancedinstaller.com/user-guide/>

```bash
python scraper.py \
  --url "https://www.advancedinstaller.com/user-guide/" \
  --crawl \
  --allowed-domain "www.advancedinstaller.com" \
  --url-prefix "https://www.advancedinstaller.com/user-guide/" \
  --max-pages 800 \
  --delay-seconds 0.2 \
  --output-dir output/advancedinstaller-user-guide
```

This configuration:
- starts from the user guide root page,
- follows links found in docs pages,
- only keeps pages inside `/user-guide/`,
- writes one `.md` file per URL.

## General usage

```bash
python scraper.py --url <page-url> [--url <page-url-2> ...] [options]
```

Options:
- `--url-file urls.txt`: read URLs from a file (one per line)
- `--crawl`: follow discovered links
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
