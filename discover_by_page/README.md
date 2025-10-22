# Books by Page Discovery Module

This module discovers all O'Reilly books by paginating through the v1 search API and organizing them by topics into individual JSON files.

## Features

- **Complete Discovery**: Paginates through all 4093 pages of the O'Reilly API
- **Topic Organization**: Automatically organizes books by their topics into separate JSON files
- **Duplicate Handling**: Tracks and skips duplicate books across all topics
- **Progress Tracking**: Saves progress and allows resuming from where you left off
- **Flexible Validation**: Uses less strict validation rules to capture more books
- **Comprehensive Logging**: Verbose and concise logging modes
- **Error Handling**: Robust error handling with retry logic

## Directory Structure

```
discover_by_page/
├── __init__.py
├── discover_books_by_page.py    # Main discovery script
├── test_discovery.py            # Test script
├── README.md                    # This file
├── book_ids/                    # Output directory for topic JSON files
│   ├── agile_books.json
│   ├── python_books.json
│   └── ...
├── output/                      # Progress tracking files
│   └── discovery_by_page_progress.json
├── book_discovery_by_page.log   # Log file
└── discovery_summary_by_page.txt # Final summary
```

## Usage

### Basic Usage

```bash
# Full discovery from scratch (all 4093 pages)
python3 discover_books_by_page.py

# Resume from last saved progress
python3 discover_books_by_page.py --resume

# Update existing library (re-process all pages)
python3 discover_books_by_page.py --update
```

### Advanced Usage

```bash
# Verbose logging
python3 discover_books_by_page.py --verbose

# Custom delay between requests (default: 1.5 seconds)
python3 discover_books_by_page.py --delay 2

# Start from specific page
python3 discover_books_by_page.py --start-page 100

# Process only specific page range
python3 discover_books_by_page.py --start-page 100 --end-page 200

# Use custom configuration file
python3 discover_books_by_page.py --config my_config.json
```

### Testing

```bash
# Run basic functionality tests
python3 test_discovery.py

# Test with small page range
python3 discover_books_by_page.py --start-page 1 --end-page 5 --verbose
```

## Configuration

The script uses these default settings:

```json
{
  "max_pages": 4093,
  "discovery_delay": 1.5,
  "resume": true,
  "progress_file": "output/discovery_by_page_progress.json",
  "verbose": false,
  "retry_failed": true,
  "max_retries": 3,
  "retry_delay": 5,
  "save_interval": 10,
  "log_file": "book_discovery_by_page.log"
}
```

## Book Validation Rules

Books are included if they meet these criteria:

- ✅ `content_type`: "book" or "ebook"
- ✅ `format`: "book" or "ebook" 
- ✅ Has valid book ID (`archive_id`, `isbn`, or `ourn`)
- ✅ Title length ≥ 4 characters
- ✅ Language: English (if specified)
- ✅ Has at least one topic in `topics` or `subjects` array

## Output Format

Each topic file follows this structure:

```json
{
  "skill_name": "Python",
  "discovery_timestamp": "2024-01-15 14:30:25",
  "total_books": 150,
  "books": [
    {
      "title": "Python Programming Guide",
      "id": "https://www.safaribooksonline.com/api/v1/book/9781234567890/",
      "url": "https://learning.oreilly.com/api/v1/book/9781234567890/",
      "isbn": "9781234567890",
      "format": "book"
    }
  ]
}
```

## Progress Tracking

The script automatically saves progress every 10 pages (configurable) to:
- `output/discovery_by_page_progress.json`

This allows you to:
- Resume from where you left off
- Track total books discovered
- Monitor duplicates skipped
- See topics created

## Logging

Two logging modes are available:

**Concise Mode (default):**
- Progress updates every 10 pages
- Major milestones only
- Final summary

**Verbose Mode (`--verbose`):**
- Logs each book added
- Shows validation failures
- API request/response details
- Debug information

## Error Handling

- **Network Issues**: Automatic retry with exponential backoff
- **API Errors**: Graceful handling with detailed error messages
- **Interruption**: Saves progress on Ctrl+C for later resumption
- **File Errors**: Continues processing even if individual files fail

## Performance

- **API Rate Limiting**: 1.5 second delay between requests (configurable)
- **Memory Efficient**: Processes one page at a time
- **Progress Saving**: Saves every 10 pages to prevent data loss
- **Duplicate Tracking**: In-memory tracking for fast duplicate detection

## Expected Results

With all 4093 pages processed, you can expect:
- **~60,000+ total items** (books, videos, courses, etc.)
- **~15,000-25,000 valid books** (after filtering)
- **~200-500 topic files** (depending on topic diversity)
- **~5-10% duplicates** (books appearing in multiple topics)

## Troubleshooting

**Common Issues:**

1. **Authentication Required**: Make sure `cookies.json` exists in the project root
2. **Network Timeouts**: Increase `discovery_delay` or `retry_delay` in config
3. **Memory Issues**: The script is designed to be memory-efficient, but very large runs may need monitoring
4. **File Permissions**: Ensure write permissions for `book_ids/` and `output/` directories

**Getting Help:**

- Check the log file: `book_discovery_by_page.log`
- Run with `--verbose` for detailed debugging
- Test with small page ranges first: `--start-page 1 --end-page 5`

