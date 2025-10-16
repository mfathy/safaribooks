# 🚀 Two-Step O'Reilly Books Automation

A comprehensive two-step system for discovering and downloading O'Reilly books organized by skills.

## 🎯 Overview

The automation system is now split into two distinct steps:

1. **🔍 Step 1: Discovery** - Find and catalog all book IDs for each skill
2. **📚 Step 2: Download** - Download actual books from the discovered IDs

This separation provides better control, resume capability, and the ability to review what will be downloaded before committing to the actual downloads.

## 📁 New File Structure

```
oreilly-books/
├── discover_book_ids.py      # Step 1: Book ID discovery
├── download_books.py         # Step 2: Book downloading
├── oreilly_automation.py     # Master coordinator
├── download_config.json      # Configuration file
└── my_favorite_skills.txt    # Your skills list
```

## 🚀 Quick Start

### Option 1: Master Coordinator (Recommended)
```bash
# Interactive mode
python3 oreilly_automation.py

# Full automation
python3 oreilly_automation.py --full

# Discovery only
python3 oreilly_automation.py --discover

# Download only
python3 oreilly_automation.py --download
```

### Option 2: Individual Commands
```bash
# Step 1: Discover all book IDs
python3 discover_book_ids.py

# Step 2: Download all books
python3 download_books.py
```

## ⚙️ Configuration

Your `download_config.json` now supports both steps:

```json
{
  "base_directory": "books_by_skills",
  "book_ids_directory": "book_ids",
  "max_books_per_skill": 1000,
  "max_pages_per_skill": 100,
  "download_delay": 5,
  "discovery_delay": 2,
  "max_workers": 2,
  "epub_format": "dual",
  "resume": true,
  "verbose": true
}
```

### Key Settings

| Setting | Purpose | Step |
|---------|---------|------|
| `max_pages_per_skill` | API pages to search | Discovery |
| `max_books_per_skill` | Books to download per skill | Download |
| `download_delay` | Delay between downloads | Download |
| `discovery_delay` | Delay between API calls | Discovery |
| `epub_format` | EPUB format (dual/enhanced/kindle) | Download |
| `verbose` | Detailed logging | Both |

## 📋 Step-by-Step Usage

### Step 1: Discovery

```bash
# Discover all skills
python3 discover_book_ids.py

# Discover specific skills
python3 discover_book_ids.py --skills "Python" "Machine Learning" "AI & ML"

# High-performance discovery
python3 discover_book_ids.py --workers 5 --max-pages 50

# Test run
python3 discover_book_ids.py --dry-run
```

**Output**: Creates `book_ids/` directory with JSON files for each skill:
```
book_ids/
├── python_books.json
├── machine-learning_books.json
├── ai-and-ml_books.json
└── ...
```

### Step 2: Download

```bash
# Download all discovered books
python3 download_books.py

# Download specific skills
python3 download_books.py --skills "Python" "Machine Learning"

# Limit books per skill
python3 download_books.py --max-books 20

# Custom EPUB format
python3 download_books.py --format enhanced

# Test run
python3 download_books.py --dry-run
```

**Output**: Creates `books_by_skills/` directory with organized books:
```
books_by_skills/
├── Python/
│   ├── Learning Python (9781449355739)/
│   │   ├── Learning Python.epub
│   │   └── Learning Python (Kindle).epub
│   └── Python Cookbook (9781449340377)/
├── Machine Learning/
└── ...
```

## 🎛️ Master Coordinator

The `oreilly_automation.py` script provides a unified interface:

### Interactive Mode
```bash
python3 oreilly_automation.py
```
Shows a menu with options:
1. Full automation (discovery + download)
2. Discovery only
3. Download only
4. Show status
5. Cleanup

### Command Line Mode
```bash
# Full automation
python3 oreilly_automation.py --full

# With custom settings
python3 oreilly_automation.py --full --workers 4 --max-books 50

# Specific skills
python3 oreilly_automation.py --full --skills "Python" "AI & ML"

# Test run
python3 oreilly_automation.py --full --dry-run
```

### Status Check
```bash
python3 oreilly_automation.py --status
```
Shows:
- Discovery progress (skills found, books cataloged)
- Download progress (skills downloaded, books saved)
- Progress files status

### Cleanup
```bash
python3 oreilly_automation.py --cleanup
```
Removes all generated files and directories.

## 📊 Progress Tracking

### Discovery Progress
- `discovery_progress.json` - Current discovery state
- `discovery_results.json` - Final discovery summary
- `discovery_summary.txt` - Human-readable summary
- `book_id_discovery.log` - Detailed discovery log

### Download Progress
- `download_progress.json` - Current download state
- `download_results.json` - Final download summary
- `book_downloader.log` - Detailed download log

## 🔄 Resume Capability

Both steps support resume:

- **Discovery**: Skips already discovered skills
- **Download**: Skips already downloaded books
- **Interrupt**: Use Ctrl+C to stop anytime
- **Resume**: Run the same command again to continue

## 🎯 Common Workflows

### Workflow 1: Full Automation
```bash
# Run everything
python3 oreilly_automation.py --full
```

### Workflow 2: Controlled Process
```bash
# Step 1: Discover
python3 discover_book_ids.py

# Review results
python3 oreilly_automation.py --status

# Step 2: Download (with limits)
python3 download_books.py --max-books 30
```

### Workflow 3: Priority Skills First
```bash
# Discover priority skills
python3 discover_book_ids.py --skills "Python" "Machine Learning" "AI & ML"

# Download priority skills
python3 download_books.py --skills "Python" "Machine Learning" "AI & ML"

# Then discover and download the rest
python3 discover_book_ids.py
python3 download_books.py
```

### Workflow 4: Testing
```bash
# Test discovery
python3 discover_book_ids.py --skills "Python" --dry-run

# Test download
python3 download_books.py --skills "Python" --dry-run

# Run actual process
python3 oreilly_automation.py --full --skills "Python"
```

## 🛡️ Safety Features

### Rate Limiting
- Configurable delays between API calls and downloads
- Respectful to O'Reilly's servers
- Adjustable concurrency levels

### Error Handling
- Failed discoveries/downloads are tracked
- Automatic retry mechanisms
- Detailed error logging

### Progress Preservation
- All progress is automatically saved
- Interruptions don't lose work
- Resume from any point

## 📈 Performance Tips

### For Large Downloads
```bash
# Conservative settings
python3 oreilly_automation.py --full --workers 1 --max-books 20

# Balanced settings
python3 oreilly_automation.py --full --workers 2 --max-books 50

# Aggressive settings (use with caution)
python3 oreilly_automation.py --full --workers 4 --max-books 100
```

### For Testing
```bash
# Small test
python3 oreilly_automation.py --full --skills "Python" --max-books 5

# Medium test
python3 oreilly_automation.py --full --skills "Python" "Machine Learning" --max-books 10
```

## 🔧 Troubleshooting

### Discovery Issues
```bash
# Check discovery status
python3 oreilly_automation.py --status

# Retry failed discoveries
python3 discover_book_ids.py --verbose
```

### Download Issues
```bash
# Check download status
python3 oreilly_automation.py --status

# Retry failed downloads
python3 download_books.py --verbose
```

### Clean Slate
```bash
# Remove everything and start fresh
python3 oreilly_automation.py --cleanup
```

## 📋 Expected Results

With your 298 skills and current configuration:

### Discovery Phase
- **Time**: 2-4 hours
- **Output**: ~298 skill files with book catalogs
- **Books Found**: Potentially 50,000+ books

### Download Phase
- **Time**: 1-3 days (depending on settings)
- **Output**: Organized books in skill folders
- **Files**: Dual EPUB format (2 files per book)

## 🎉 Benefits of Two-Step System

1. **🔍 Transparency**: See exactly what will be downloaded
2. **⚡ Flexibility**: Run steps independently
3. **🛡️ Safety**: Test before committing to large downloads
4. **🔄 Resume**: Better progress tracking and resume capability
5. **📊 Analysis**: Review discovery results before downloading
6. **⚙️ Control**: Fine-tune each step separately

---

**Ready to start?** Run `python3 oreilly_automation.py` for guided setup!

