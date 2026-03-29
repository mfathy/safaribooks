# O'Reilly Books Project - Complete Specifications

This document provides a comprehensive reference for all features, commands, options, inputs, and outputs in the O'Reilly Books downloader project.

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Feature Specifications](#2-feature-specifications)
3. [Commands Reference](#3-commands-reference)
4. [Input/Output Reference](#4-inputoutput-reference)
5. [Configuration Files](#5-configuration-files)

---

## 1. Project Overview

**Purpose:** Download EPUB books from O'Reilly Learning platform, organized by skill categories or as a flat catalog.

**Requirements:** Python 3.x, dependencies via `pip install -r requirements.txt`

**Authentication:** Cookie-based (`cookies.json`) — see `docs/COOKIE_SETUP.md`

---

## 2. Feature Specifications

### 2.1 Two-Step Workflow
| Aspect | Specification |
|--------|---------------|
| **Step 1** | Discovery — find book IDs for skills via API |
| **Step 2** | Download — fetch books and generate EPUBs |
| **Resume** | Auto-resume on interruption; progress saved in JSON |
| **Separation** | Discovery and download run independently |

### 2.2 EPUB Formats
| Format | Specification |
|--------|---------------|
| `legacy` | EPUB 2.0 format |
| `enhanced` | EPUB 3.3 standard format |
| `kindle` | EPUB 3.3 Kindle-optimized format |
| `dual` | Generates both standard EPUB + Kindle EPUB |

### 2.3 Book Source Formats
| Format | Description | Organization |
|--------|-------------|--------------|
| **Skill-based** | Multiple JSON files in `book_ids/` | `books_by_skills/[Skill Name]/` |
| **Single JSON** | One flat array with all books | `books_by_skills/All Books/` |

### 2.4 Rate Limiting & Delays
- **download_delay**: Seconds between download requests
- **discovery_delay**: Seconds between API discovery requests
- **discovery_by_page delay**: Configurable per-page delay

### 2.5 Progress & Resume
- JSON state files for discovery and download
- Completed/failed item tracking
- ETA support in automation script

### 2.6 Sound Notifications (macOS)
- Optional sound on download completion (`afplay`)
- Configurable via `--no-sound` or `--sound-file`
- Enable/disable in `download_config.json`

### 2.7 Skill Management
- **all**: Uses `skills/output/all_skills_organized.json`
- **favorites**: Uses `skills/output/favorite_skills_organized.json`
- Skills pipeline: `skills/organize_skills.py` merges inputs to `skills/output/`

### 2.8 Discovery Methods
| Method | Auth Required | API | Use Case |
|--------|---------------|-----|----------|
| **V1** (`discover_book_ids.py`) | Yes (cookies) | v1 search | Skill-based discovery |
| **V2** (`discover_book_ids_v2.py`) | No | v2 public search | Same without auth |
| **By Page** (`discover_books_by_page.py`) | Yes (cookies) | v1 pagination | Full catalog, topic-organized |

---

## 3. Commands Reference

### 3.1 Single Book Download

#### `oreilly_books.py`
**Purpose:** Download one book by ID.

```bash
python3 oreilly_books.py [bookid]
```

| Argument/Option | Type | Description |
|-----------------|------|-------------|
| `bookid` | positional (optional) | Book digits from URL: `learning.oreilly.com/library/view/book-name/XXXXXXXXXXXXX/` |
| `--cred <EMAIL:PASS>` | string | Credentials — **blocked** (use cookies) |
| `--login` | flag | Interactive login — **blocked** (use cookies) |
| `--no-cookies` | flag | Only valid with `--cred` |
| `--kindle` | flag | Kindle-optimized EPUB |
| `--enhanced` | flag | EPUB 3.3 standard |
| `--dual` | flag | Both standard + Kindle |
| `--preserve-log` | flag | Keep `info_<bookid>.log` after run |
| `--help` | flag | Show help |

**Example:**
```bash
python3 oreilly_books.py 9781119931355 --dual
```

---

#### `safaribooks.py` (Legacy)
**Purpose:** Legacy Safari Books–style single-book download.

```bash
python3 safaribooks.py <bookid>
```

| Argument/Option | Type | Description |
|-----------------|------|-------------|
| `bookid` | required | Book ID |
| `--cred`, `--login` | flags | **Blocked** — use cookies |
| `--no-cookies` | flag | Disable cookies |
| `--kindle` | flag | Kindle format |
| `--preserve-log` | flag | Keep log file |
| `--help` | flag | Show help |

---

### 3.2 Discovery Commands

#### `discover_book_ids.py`
**Purpose:** Discover book IDs for skills (V1 API, requires authentication).

```bash
python3 discover_book_ids.py [options]
```

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | path | — | Configuration file path |
| `--skills` | `-s` | strings+ | — | Specific skills to discover |
| `--skills-source` | — | choice | `all` | `all` \| `favorites` |
| `--max-pages` | — | int | config | API pages per skill |
| `--workers` | — | int | config | Concurrent discovery threads |
| `--verbose` | `-v` | flag | — | Verbose logging |
| `--update` | `-u` | flag | — | Re-discover already discovered skills |
| `--dry-run` | — | flag | — | Preview without discovering |

**Examples:**
```bash
python3 discover_book_ids.py
python3 discover_book_ids.py --skills "Python" "Machine Learning"
python3 discover_book_ids.py --skills-source favorites --dry-run
```

---

#### `discover_v2/discover_book_ids_v2.py`
**Purpose:** Same as above but uses V2 public API (no authentication).

```bash
cd discover_v2 && python3 discover_book_ids_v2.py [options]
```

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | path | — | Configuration file path |
| `--skills` | `-s` | strings+ | — | Specific skills |
| `--skills-source` | — | choice | `all` | `all` \| `favorites` |
| `--max-pages` | — | int | config | API pages per skill |
| `--workers` | — | int | config | Concurrent threads |
| `--verbose` | `-v` | flag | — | Verbose logging |
| `--update` | `-u` | flag | — | Re-discover skills |
| `--dry-run` | — | flag | — | Preview only |

---

#### `discover_by_page/discover_books_by_page.py`
**Purpose:** Paginate through full catalog, organize by topic.

```bash
cd discover_by_page && python3 discover_books_by_page.py [options]
```

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | path | — | Configuration file |
| `--start-page` | — | int | 1 | First page |
| `--end-page` | — | int | 4093 | Last page |
| `--delay` | — | float | config | Delay between requests (sec) |
| `--verbose` | `-v` | flag | — | Verbose logging |
| `--update` | `-u` | flag | — | Re-process all pages |
| `--resume` | `-r` | flag | — | Resume from saved progress |

**Examples:**
```bash
python3 discover_books_by_page.py
python3 discover_books_by_page.py --resume
python3 discover_books_by_page.py --start-page 100 --end-page 200 --verbose
```

---

### 3.3 Batch Download

#### `download_books.py`
**Purpose:** Download books from discovered IDs or single JSON.

```bash
python3 download_books.py [options]
```

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | path | — | Configuration file |
| `--skills` | `-s` | strings+ | — | Filter skills (skill-based format only) |
| `--json-file` | `-j` | path | — | Single JSON file (new format) |
| `--max-books` | — | int | config | Max books per skill or total |
| `--format` | — | choice | config | `legacy` \| `enhanced` \| `kindle` \| `dual` |
| `--force` | `-f` | flag | — | Re-download even if EPUB exists |
| `--token-save-interval` | — | int | 5 | Save cookies after N books |
| `--verbose` | `-v` | flag | — | Verbose logging |
| `--dry-run` | — | flag | — | Preview without downloading |
| `--no-sound` | — | flag | — | Disable completion sound |
| `--sound-file` | — | path | — | Custom sound file path |

**Examples:**
```bash
# Skill-based
python3 download_books.py
python3 download_books.py --skills "Python" "AI & ML"
python3 download_books.py --format dual --max-books 20

# Single JSON
python3 download_books.py --json-file oreilly-books-2026-01-25.json
python3 download_books.py -j oreilly-books-2026-01-25.json --force --dry-run
```

---

### 3.4 Interactive & Automation

#### `quick_download.py`
**Purpose:** Interactive wizard for discovery and download.

```bash
python3 quick_download.py
```

**No CLI options.** Prompts for:
1. JSON format (skill-based vs single file)
2. Discovery options (if applicable)
3. Download options

---

#### `oreilly_automation.py`
**Purpose:** Master coordinator for discovery + download; subprocess orchestration.

```bash
python3 oreilly_automation.py [options]
```

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | path | — | Configuration file |
| `--full` | — | flag | — | Run discovery + download |
| `--discover` | — | flag | — | Discovery only |
| `--download` | — | flag | — | Download only |
| `--status` | — | flag | — | Show current status |
| `--progress` | — | flag | — | Show detailed progress + ETA |
| `--progress-type` | — | choice | `all` | `all` \| `discovery` \| `download` |
| `--cleanup` | — | flag | — | Clean up generated files |
| `--skills` | `-s` | strings+ | — | Skills to process |
| `--max-pages` | — | int | — | Pages per skill (discovery) |
| `--max-books` | — | int | — | Books per skill (download) |
| `--workers` | — | int | — | Concurrent threads |
| `--format` | — | choice | — | EPUB format |
| `--verbose` | `-v` | flag | — | Verbose logging |
| `--dry-run` | — | flag | — | Preview only |

**Interactive menu (no step flag):** Options 1–6 for various workflows.

---

### 3.5 Post-Download & Utilities

#### `organize_books.py`
**Purpose:** Move books into an "All Books" folder from skill-based structure.

```bash
python3 organize_books.py [options]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--json` | path | `oreilly-books-2026-01-25.json` | JSON with book IDs |
| `--books-dir` | path | `books_by_skills` | Books directory |
| `--all-books-dir` | string | `All Books` | Target folder name |
| `--dry-run` | flag | — | Preview without moving |
| `--log-file` | path | `book_organization.log` | Log output path |

---

#### `deduplicate_book_ids.py`
**Purpose:** Merge and deduplicate book IDs across `book_ids`, backups, and discover_v2.

```bash
python3 deduplicate_book_ids.py
```

**No CLI arguments.** Uses hard-coded paths inside the script.

---

#### `skills/organize_skills.py`
**Purpose:** Merge skill inputs into organized JSON for discovery.

```bash
cd skills && python3 organize_skills.py
```

**No argparse.** Reads `skills/input/`, writes `skills/output/`.

---

## 4. Input/Output Reference

### 4.1 Single Book

| Command | Inputs | Outputs |
|---------|--------|---------|
| `oreilly_books.py` | `bookid`, `cookies.json` | EPUB under project tree; `info_<bookid>.log` (optional) |
| `safaribooks.py` | Same | `Books/<id>/` with EPUB/zip |

### 4.2 Discovery

| Command | Inputs | Outputs |
|---------|--------|---------|
| `discover_book_ids.py` | `cookies.json`, skills from config/`--skills` | `book_ids/<skill>_books.json`, `output/discovery_progress.json`, `discovery_results.json`, `discovery_summary.txt` |
| `discover_book_ids_v2.py` | Config, skills (no cookies) | `discover_v2/book_ids/`, `discovery_results_v2.json`, `discovery_summary_v2.txt`, `output/discovery_progress.json`, `book_id_discovery_v2.log` |
| `discover_books_by_page.py` | `cookies.json`, config | `discover_by_page/book_ids/`, `output/discovery_by_page_progress.json`, `book_discovery_by_page.log`, `discovery_summary_by_page.txt` |

### 4.3 Batch Download

| Command | Inputs | Outputs |
|---------|--------|---------|
| `download_books.py` | `cookies.json`, `book_ids/*.json` or `--json-file`, config | `books_by_skills/`, `output/download_progress.json`, `output/download_results.json`, `output/download_progress_live.txt`, `logs/book_downloader.log` |

### 4.4 Utilities

| Command | Inputs | Outputs |
|---------|--------|---------|
| `organize_books.py` | JSON catalog, `books_by_skills/` tree | `All Books/` (or `--all-books-dir`), `book_organization.log` |
| `deduplicate_book_ids.py` | Hard-coded dirs | Backups, merged `book_ids/`, `merge_and_deduplication_report.json` |
| `organize_skills.py` | `skills/input/*` | `skills/output/all_skills_organized.json`, `favorite_skills_organized.json` |

### 4.5 JSON Formats

**Skill-based (book_ids):**
```json
{
  "skill_name": "Python",
  "books": [
    {
      "id": "https://www.safaribooksonline.com/api/v1/book/9781119931355/",
      "title": "Book Title",
      "isbn": "9781119931355"
    }
  ]
}
```

**Single file (new format):**
```json
[
  {
    "bookId": "9781633438125",
    "title": "Book Title",
    "authors": ["Author"],
    "isbn": "9781633438125",
    "url": "https://learning.oreilly.com/library/view/-/9781633438125/"
  }
]
```

---

## 5. Configuration Files

### 5.1 `download_config.json` (root)

| Key | Purpose |
|-----|---------|
| `base_directory` | Download output directory (e.g. `books`, `books_by_skills`) |
| `book_ids_directory` | Discovery output directory |
| `temp_directory` | Temp files |
| `max_books_per_skill` | Limit per skill |
| `max_pages_per_skill` | API pages per skill |
| `download_delay` | Seconds between downloads |
| `discovery_delay` | Seconds between discovery requests |
| `max_workers` | Concurrent threads |
| `epub_format` | `legacy` / `enhanced` / `kindle` / `dual` |
| `resume` | Enable resume |
| `force_redownload` | Re-download existing |
| `token_save_interval` | Save cookies every N books |
| `skills_file` | Skills list (e.g. `my_favorite_skills.txt`) |
| `progress_file` | Download progress JSON |
| `discovery_progress_file` | Discovery progress JSON |
| `exclude_skills` | Skills to skip |
| `priority_skills` | Skills to prioritize |
| `enable_sound_notifications` | Sound on completion |
| `sound_file` | Custom sound path |
| `progress_stats_file` | Live stats file (e.g. `output/download_progress_live.txt`) |

### 5.2 `discover_v2/config.json`

V2 discovery settings: `book_ids_directory`, pagination, workers, delays, `skills_file`, progress, retries, excludes.

### 5.3 `discover_v2/config_skills_facets.json`

Same as above; `skills_file` points to facets format.

### 5.4 `config.py` (Python)

URLs, headers, HTML/EPUB templates, `COOKIES_FILE` path.

### 5.5 `cookies.json` (user-provided)

Browser-exported session cookies for O'Reilly Learning.

---

## Quick Reference: Common Workflows

| Goal | Commands |
|------|----------|
| Single book | `python3 oreilly_books.py 9781119931355` |
| Interactive full flow | `python3 quick_download.py` |
| Discover + download (manual) | `python3 discover_book_ids.py` then `python3 download_books.py` |
| Discover without auth | `cd discover_v2 && python3 discover_book_ids_v2.py` |
| Full catalog by topic | `cd discover_by_page && python3 discover_books_by_page.py` |
| Download from single JSON | `python3 download_books.py -j oreilly-books-2026-01-25.json` |
| Organize into All Books | `python3 organize_books.py --json oreilly-books-2026-01-25.json` |

---

*Last updated: March 2026*
