# O'Reilly Books Automation Guide

This guide explains how to use the automated book downloader to organize your O'Reilly books by skills.

## Overview

The automation script (`automate_skill_downloads.py`) will:
1. Read your favorite skills from `my_favorite_skills.txt`
2. Search for books in each skill category
3. Download books organized in skill-specific folders
4. Track progress and allow resuming interrupted downloads
5. Generate enhanced EPUB files with proper metadata

## Quick Start

### 1. Basic Usage
```bash
# Download all books for your favorite skills
python automate_skill_downloads.py
```

### 2. Download Specific Skills
```bash
# Download only Python and Machine Learning books
python automate_skill_downloads.py --skills "Python" "Machine Learning" "AI & ML"
```

### 3. Test Run (Dry Run)
```bash
# See what would be downloaded without actually downloading
python automate_skill_downloads.py --dry-run
```

## Configuration

### Configuration File
Create or modify `download_config.json` to customize behavior:

```json
{
  "base_directory": "books_by_skills",
  "max_books_per_skill": 30,
  "max_pages_per_skill": 3,
  "download_delay": 3,
  "max_workers": 2,
  "epub_format": "enhanced",
  "resume": true,
  "skills_file": "my_favorite_skills.txt",
  "progress_file": "download_progress.json",
  "verbose": false,
  "retry_failed": true,
  "max_retries": 3,
  "retry_delay": 10,
  "priority_skills": [
    "Python",
    "Machine Learning", 
    "AI & ML"
  ]
}
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `base_directory` | Base folder for organized books | `books_by_skills` |
| `max_books_per_skill` | Max books to download per skill | `30` |
| `max_pages_per_skill` | Max API pages to search per skill | `3` |
| `download_delay` | Delay between downloads (seconds) | `3` |
| `max_workers` | Concurrent download threads | `2` |
| `epub_format` | EPUB format: `legacy`, `enhanced`, `kindle`, `dual` | `enhanced` |
| `resume` | Resume interrupted downloads | `true` |
| `verbose` | Detailed logging | `false` |
| `retry_failed` | Retry failed downloads | `true` |
| `max_retries` | Max retry attempts | `3` |

## Command Line Options

```bash
python automate_skill_downloads.py [OPTIONS]

Options:
  --config, -c FILE        Configuration file path
  --skills, -s SKILLS      Specific skills to download
  --max-books N           Maximum books per skill
  --max-pages N           Maximum API pages per skill
  --workers N             Number of concurrent threads
  --format FORMAT         EPUB format (legacy/enhanced/kindle/dual)
  --verbose, -v           Verbose logging
  --dry-run               Show what would be downloaded
```

## Folder Structure

After running the automation, your books will be organized like this:

```
books_by_skills/
├── Python/
│   ├── Learning Python (9781449355739)/
│   │   ├── Learning Python.epub
│   │   └── OEBPS/
│   └── Python Cookbook (9781449340377)/
│       ├── Python Cookbook.epub
│       └── OEBPS/
├── Machine Learning/
│   ├── Hands-On Machine Learning (9781492032649)/
│   │   ├── Hands-On Machine Learning.epub
│   │   └── OEBPS/
│   └── Pattern Recognition and Machine Learning (9780387310732)/
│       ├── Pattern Recognition and Machine Learning.epub
│       └── OEBPS/
└── AI & ML/
    └── ...
```

## Progress Tracking

The script automatically tracks progress:

- **Progress file**: `download_progress.json` - tracks downloaded and failed books
- **Results file**: `download_results.json` - detailed results after completion
- **Log file**: `skill_downloader.log` - detailed execution log

### Resuming Downloads

If the download is interrupted, simply run the script again:
```bash
python automate_skill_downloads.py
```

The script will automatically:
- Skip already downloaded books
- Retry failed downloads
- Continue from where it left off

## Examples

### Example 1: Download Top 20 Books for AI Skills
```bash
python automate_skill_downloads.py \
  --skills "AI & ML" "Machine Learning" "Deep Learning" \
  --max-books 20 \
  --max-pages 2 \
  --format enhanced
```

### Example 2: Custom Configuration
```bash
# Use custom config file
python automate_skill_downloads.py --config my_custom_config.json

# Override specific settings
python automate_skill_downloads.py \
  --config my_custom_config.json \
  --max-books 50 \
  --workers 4
```

### Example 3: Test Run for Specific Skills
```bash
# See what would be downloaded for Python
python automate_skill_downloads.py --skills "Python" --dry-run
```

## Tips and Best Practices

### 1. Start Small
Begin with a few skills and limited books to test:
```bash
python automate_skill_downloads.py --skills "Python" --max-books 5 --dry-run
```

### 2. Use Appropriate Delays
Set reasonable delays to avoid overwhelming O'Reilly's servers:
```bash
python automate_skill_downloads.py --workers 1 --max-books 10
```

### 3. Monitor Progress
Check the log file for detailed progress:
```bash
tail -f skill_downloader.log
```

### 4. Prioritize Important Skills
Modify `download_config.json` to prioritize your most important skills:
```json
{
  "priority_skills": [
    "Python",
    "Machine Learning",
    "Data Science"
  ]
}
```

### 5. Handle Large Downloads
For large downloads (100+ skills), consider:
- Running overnight
- Using smaller `max_workers` (1-2)
- Increasing `download_delay` (5+ seconds)
- Running in batches by skill categories

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure `cookies.json` is properly set up
   - Check that your O'Reilly subscription is active

2. **Rate Limiting**
   - Increase `download_delay` in config
   - Reduce `max_workers` to 1
   - Check `skill_downloader.log` for rate limit messages

3. **Disk Space**
   - Monitor available disk space
   - Consider reducing `max_books_per_skill`

4. **Network Issues**
   - The script will retry failed downloads
   - Check your internet connection
   - Consider running during off-peak hours

### Logs and Debugging

Enable verbose logging for detailed information:
```bash
python automate_skill_downloads.py --verbose
```

Check log files:
- `skill_downloader.log` - Main execution log
- `download_progress.json` - Current progress state
- `download_results.json` - Final results summary

## Advanced Usage

### Custom Skill Lists
Create custom skill files:
```bash
# Create custom skills file
echo -e "Python\nMachine Learning\nDeep Learning" > my_ai_skills.txt

# Use custom skills file
python automate_skill_downloads.py --config config_with_custom_skills.json
```

### Batch Processing
Process skills in batches:
```bash
# First batch: Core programming
python automate_skill_downloads.py --skills "Python" "Java" "JavaScript" "Go"

# Second batch: AI/ML
python automate_skill_downloads.py --skills "Machine Learning" "Deep Learning" "AI & ML"

# Third batch: Data Science
python automate_skill_downloads.py --skills "Data Science" "Statistics" "Analytics"
```

## Support

If you encounter issues:
1. Check the log files for error messages
2. Try running with `--verbose` for more details
3. Start with `--dry-run` to test configuration
4. Reduce concurrency and increase delays if experiencing rate limits

The automation script is designed to be robust and resumable, so you can safely interrupt and restart downloads as needed.
