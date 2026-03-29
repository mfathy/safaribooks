# 📚 O'Reilly Books Download Flows

This document describes both methods for downloading books from O'Reilly.

---

## 🎯 Method 1: Current Format (Skill-Based)

### Overview
Downloads books organized by skills from JSON files in the `book_ids/` directory.

### Prerequisites
- `cookies.json` file with authentication
- `book_ids/` directory with skill-based JSON files (e.g., `agile_books.json`, `python_books.json`)

### Flow

#### Step 1: Discovery (if needed)
If `book_ids/` directory doesn't exist or is empty:

```
Select discovery option:
1. Discover all skills from my_favorite_skills.txt
2. Discover specific skills
3. Skip discovery (exit)
```

**Option 1**: Discovers books for all skills listed in `my_favorite_skills.txt`
```bash
python3 discover_book_ids.py
```

**Option 2**: Discovers books for specific skills
```bash
python3 discover_book_ids.py --skills "Python" "Machine Learning" "AI"
```

**Result**: Creates JSON files in `book_ids/` directory:
- `book_ids/agile_books.json`
- `book_ids/python_books.json`
- etc.

Each file contains:
```json
{
  "skill_name": "Agile",
  "books": [
    {
      "id": "https://www.safaribooksonline.com/api/v1/book/9781119931355/",
      "title": "The Project Manager's Guide to Mastering Agile",
      "isbn": "9781119931355"
    }
  ]
}
```

#### Step 2: Download Books

**Via `quick_download.py` (Interactive):**
```
Select download option:
1. Download all discovered books
2. Download specific skills
3. Test run (dry run)
4. Download priority skills only
5. Force re-download all books (updates existing)
6. Custom configuration
```

**Option 1: Download all discovered books**
- Downloads all books from all skill JSON files
- Books organized in `books_by_skills/` by skill name
- Skips already downloaded books
```bash
python3 download_books.py
```

**Option 2: Download specific skills**
- Filters to only specified skills
- Example: Download only "Python" and "Machine Learning" books
```bash
python3 download_books.py --skills "Python" "Machine Learning"
```

**Option 3: Test run (dry run)**
- Shows what would be downloaded without actually downloading
- Useful for previewing the download plan
```bash
python3 download_books.py --dry-run
```

**Option 4: Download priority skills only**
- Downloads predefined priority skills with limit
- Priority skills: Python, Machine Learning, AI & ML, Data Science, Deep Learning
- Limits to 20 books per skill
```bash
python3 download_books.py --skills "Python" "Machine Learning" "AI & ML" "Data Science" "Deep Learning" --max-books 20
```

**Option 5: Force re-download all books**
- Re-downloads all books even if EPUB files already exist
- Overwrites existing files
```bash
python3 download_books.py --force
```

**Option 6: Custom configuration**
- Set EPUB format (legacy/enhanced/kindle/dual)
- Set max books per skill
- Force re-download toggle
- Token save interval
```bash
python3 download_books.py --format dual --max-books 50 --force --token-save-interval 10
```

**Direct Command Line Options:**
```bash
# Basic download
python3 download_books.py

# With filters
python3 download_books.py --skills "Python" "AI"

# With limits
python3 download_books.py --max-books 20

# EPUB format options
python3 download_books.py --format dual      # Standard + Kindle
python3 download_books.py --format enhanced  # EPUB 3.3 Standard
python3 download_books.py --format kindle    # EPUB 3.3 Kindle-optimized
python3 download_books.py --format legacy    # EPUB 2.0

# Force re-download
python3 download_books.py --force

# Custom config file
python3 download_books.py --config my_config.json

# Verbose logging
python3 download_books.py --verbose

# Disable sound notifications
python3 download_books.py --no-sound
```

### Output Structure
```
books_by_skills/
├── Agile/
│   ├── Book Title 1 (9781119931355)/
│   └── Book Title 2 (9781780176635)/
├── Python/
│   └── ...
└── Machine Learning/
    └── ...
```

---

## 🆕 Method 2: New Format (Single JSON File)

### Overview
Downloads all books from a single JSON file containing all books in a flat array format.

### Prerequisites
- `cookies.json` file with authentication
- Single JSON file with all books (e.g., `oreilly-books-2026-01-25.json`)

### JSON File Format
```json
[
  {
    "bookId": "9781633438125",
    "title": "\"Looks Good to Me\"",
    "authors": ["Adrienne Braganza"],
    "isbn": "9781633438125",
    "publisher": "O'Reilly Media",
    "skills": [],
    "url": "https://learning.oreilly.com/library/view/-/9781633438125/"
  },
  {
    "bookId": "9781564147752",
    "title": "100 Ways to Motivate Yourself",
    "authors": ["Steve Chandler"],
    "isbn": "9781564147752",
    ...
  }
]
```

### Flow

#### Step 1: Format Selection
When running `quick_download.py`, select:
```
Select JSON format:
1. Current format (skill-based JSON files from book_ids/ directory)
2. New format (single JSON file with all books)
```

Choose **Option 2**, then provide the JSON file path:
```
Enter path to JSON file: oreilly-books-2026-01-25.json
```

**Note**: Discovery step is skipped automatically when using new format.

#### Step 2: Download Books

**Via `quick_download.py` (Interactive):**
```
Select download option:
1. Download all books from JSON file
2. Test run (dry run) - preview what would be downloaded
3. Force re-download all books (updates existing)
4. Custom configuration (EPUB format, token settings, etc.)
```

**Option 1: Download all books from JSON file**
- Downloads all books sequentially from the JSON file
- Books saved to `books_by_skills/All Books/`
- Skips already downloaded books
```bash
python3 download_books.py --json-file oreilly-books-2026-01-25.json
```

**Option 2: Test run (dry run)**
- Shows what would be downloaded without actually downloading
- Displays total book count
```bash
python3 download_books.py --json-file oreilly-books-2026-01-25.json --dry-run
```

**Option 3: Force re-download all books**
- Re-downloads all books even if EPUB files already exist
- Overwrites existing files
```bash
python3 download_books.py --json-file oreilly-books-2026-01-25.json --force
```

**Option 4: Custom configuration**
- Set EPUB format (legacy/enhanced/kindle/dual)
- Set max books limit (applies to total, not per skill)
- Force re-download toggle
- Token save interval
```bash
python3 download_books.py --json-file oreilly-books-2026-01-25.json --format dual --max-books 100 --force --token-save-interval 10
```

**Direct Command Line Options:**
```bash
# Basic download
python3 download_books.py --json-file oreilly-books-2026-01-25.json

# With limits
python3 download_books.py --json-file oreilly-books-2026-01-25.json --max-books 100

# EPUB format options
python3 download_books.py --json-file oreilly-books-2026-01-25.json --format dual
python3 download_books.py --json-file oreilly-books-2026-01-25.json --format enhanced
python3 download_books.py --json-file oreilly-books-2026-01-25.json --format kindle
python3 download_books.py --json-file oreilly-books-2026-01-25.json --format legacy

# Force re-download
python3 download_books.py --json-file oreilly-books-2026-01-25.json --force

# Dry run
python3 download_books.py --json-file oreilly-books-2026-01-25.json --dry-run

# Verbose logging
python3 download_books.py --json-file oreilly-books-2026-01-25.json --verbose
```

### Output Structure
```
books_by_skills/
└── All Books/
    ├── Book Title 1 (9781633438125)/
    ├── Book Title 2 (9781564147752)/
    └── ...
```

### Important Notes
- **No skill filtering**: All books from the JSON file are downloaded
- **No skill organization**: All books go to `books_by_skills/All Books/`
- **Sequential download**: Books are downloaded one by one until finished
- **Progress tracking**: Uses same progress tracking system as current format

---

## 🔄 Comparison Table

| Feature | Current Format | New Format |
|---------|---------------|------------|
| **Source** | Multiple JSON files in `book_ids/` | Single JSON file |
| **Organization** | By skill (e.g., `Agile/`, `Python/`) | Single folder (`All Books/`) |
| **Discovery Required** | Yes (unless files exist) | No |
| **Skill Filtering** | ✅ Yes | ❌ No |
| **Book ID Format** | `id` (URL or ISBN) | `bookId` (ISBN) |
| **Use Case** | Organized by topics/skills | Bulk download all books |
| **Download Options** | 6 options | 4 options |

---

## 🚀 Quick Start Examples

### Current Format - Download All Books
```bash
python3 quick_download.py
# Select: 1 (Current format)
# Select: 1 (Download all discovered books)
```

### Current Format - Download Specific Skills
```bash
python3 quick_download.py
# Select: 1 (Current format)
# Select: 2 (Download specific skills)
# Enter: Python, Machine Learning
```

### New Format - Download All Books
```bash
python3 quick_download.py
# Select: 2 (New format)
# Enter: oreilly-books-2026-01-25.json
# Select: 1 (Download all books from JSON file)
```

### New Format - Force Re-download
```bash
python3 download_books.py --json-file oreilly-books-2026-01-25.json --force
```

---

## 📊 Common Options (Both Formats)

### EPUB Formats
- `dual`: Generates both standard EPUB and Kindle-optimized EPUB
- `enhanced`: EPUB 3.3 standard format
- `kindle`: EPUB 3.3 Kindle-optimized format
- `legacy`: EPUB 2.0 format

### Other Options
- `--max-books N`: Limit number of books (per skill for current format, total for new format)
- `--force`: Force re-download even if EPUB exists
- `--dry-run`: Preview without downloading
- `--verbose`: Detailed logging
- `--token-save-interval N`: Save cookies after N books (default: 5)
- `--no-sound`: Disable sound notifications
- `--config FILE`: Use custom configuration file

---

## 📁 Output Locations

Both formats save results to:
- **Books**: `books_by_skills/` directory
- **Progress**: `output/download_progress.json`
- **Live Stats**: `output/download_progress_live.txt`
- **Results**: `output/download_results.json`
- **Logs**: `logs/book_downloader.log`

---

## 💡 Tips

1. **Resume Downloads**: Both formats support resuming. If interrupted, just run the same command again - already downloaded books will be skipped.

2. **Monitor Progress**: Use `tail -f output/download_progress_live.txt` in another terminal to see live progress.

3. **Dry Run First**: Always test with `--dry-run` first to see what will be downloaded.

4. **Token Management**: The downloader automatically saves cookies every N books (default: 5) to keep authentication fresh.

5. **Format Choice**: Use `dual` format if you want both standard and Kindle versions. Use `enhanced` for best compatibility.
