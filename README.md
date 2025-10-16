# O'Reilly Books Downloader

Download EPUB books from O'Reilly Learning platform, organized by skill categories.

## Requirements

- Python 3.x
- Dependencies:
  ```bash
  pip install -r requirements.txt
  ```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup authentication:**
   - Log in to [O'Reilly Learning](https://learning.oreilly.com) in your browser
   - Copy cookies to `cookies.json` (see `docs/COOKIE_SETUP.md`)

3. **Configure skills (optional):**
   - Edit `my_favorite_skills.txt` with your favorite skills (one per line)

## Usage

### Quick Start (Interactive)
```bash
python3 quick_download.py
```
Follow the prompts to discover and download books.

### Two-Step Manual Process

#### Step 1: Discover Book IDs
```bash
python3 discover_book_ids.py
```
Discovers all book IDs for skills in `my_favorite_skills.txt`

#### Step 2: Download Books
```bash
python3 download_books.py
```
Downloads books from discovered IDs, organized by skill folders

### Download Single Book
```bash
python3 oreilly_books.py BOOK_ID
```
Book ID is the number in the URL: `https://learning.oreilly.com/library/view/book-name/XXXXXXXXXXXXX/`

## Command Options

### Discovery Options
```bash
python3 discover_book_ids.py --skills "Python" "Machine Learning"  # Specific skills
python3 discover_book_ids.py --dry-run                             # Test run
```

### Download Options
```bash
python3 download_books.py --skills "Python" "AI & ML"              # Specific skills
python3 download_books.py --max-books 20                           # Limit per skill
python3 download_books.py --format dual                            # EPUB format (legacy/enhanced/kindle/dual)
python3 download_books.py --dry-run                                # Test run
```

## Output Structure

```
oreilly-books/
├── books_by_skills/          # Downloaded books organized by skill
│   └── [Skill Name]/
│       └── [Book Title (ID)]/
│           ├── OEBPS/
│           │   ├── *.xhtml
│           │   ├── Images/
│           │   └── Styles/
│           └── *.epub
├── book_ids/                 # Discovered book IDs (JSON)
├── output/                   # Progress and results
│   ├── download_progress.json
│   ├── download_results.json
│   └── discovery_progress.json
└── logs/                     # Execution logs
    ├── book_downloader.log
    └── info_[BOOK_ID].log
```

## Features

- **Two-step workflow**: Separate discovery and download
- **Progress tracking**: Auto-resume on interruption
- **Skill organization**: Books organized in skill-based folders
- **Multiple formats**: Legacy EPUB, Enhanced EPUB 3.3, Kindle-optimized, or Dual
- **Rate limiting**: Built-in delays to prevent API issues

## Troubleshooting

- **Authentication issues**: See `docs/COOKIE_SETUP.md`
- **Rate limiting**: Increase delay with `--delay` option
- **Resume downloads**: Just run the command again

## Documentation

See `docs/` folder for detailed documentation.

## Disclaimer

For personal and educational purposes only. Please respect [O'Reilly's Terms of Service](https://learning.oreilly.com/terms/).
