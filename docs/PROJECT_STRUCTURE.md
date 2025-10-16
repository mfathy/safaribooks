# Project Structure

## Directory Layout

```
oreilly-books/
├── README.md                      # Main documentation (requirements & usage)
├── requirements.txt               # Python dependencies
├── cookies.json                   # Authentication cookies (user-provided)
├── my_favorite_skills.txt         # List of skills to download
│
├── Main Scripts
├── oreilly_books.py               # CLI for single book downloads
├── discover_book_ids.py           # Step 1: Discover book IDs
├── download_books.py              # Step 2: Download books
├── quick_download.py              # Interactive interface
├── config.py                      # Configuration constants
├── progress_tracker.py            # Progress tracking module
│
├── Core Modules
├── oreilly_books/                 # Download library
│   ├── __init__.py
│   ├── core.py                    # Main orchestrator
│   ├── auth.py                    # Authentication
│   ├── download.py                # Book downloader
│   ├── epub_legacy.py             # EPUB 2.0 generator
│   ├── epub_enhanced.py           # EPUB 3.3 generator
│   └── display.py                 # Logging/display
│
├── oreilly_parser/                # API parsing utilities
│   ├── oreilly_books_parser.py    # Book metadata parser
│   └── oreilly_skills_parser.py   # Skills discovery parser
│
├── Output Directories
├── book_ids/                      # Discovered book IDs (JSON files)
├── books_by_skills/               # Downloaded books organized by skill
│   └── [Skill Name]/
│       └── [Book Title (ID)]/
│           ├── OEBPS/
│           └── *.epub
├── logs/                          # All log files
│   ├── book_downloader.log        # Download execution log
│   └── info_[BOOK_ID].log         # Individual book logs
├── output/                        # Progress and results
│   ├── download_progress.json     # Download progress state
│   ├── download_results.json      # Download summary
│   └── discovery_progress.json    # Discovery progress state
│
└── Documentation
    └── docs/                      # All documentation files
        ├── PROJECT_STRUCTURE.md   # This file
        ├── COOKIE_SETUP.md        # Authentication setup
        └── [other .md files]
```

## File Purposes

### Main Scripts
- **oreilly_books.py**: Entry point for downloading a single book by ID
- **discover_book_ids.py**: Discovers all book IDs for specified skills
- **download_books.py**: Downloads books from discovered IDs (serial processing)
- **quick_download.py**: Interactive wizard for the complete workflow

### Configuration
- **config.py**: URLs, headers, HTML/EPUB templates, constants
- **cookies.json**: O'Reilly authentication cookies (must be provided by user)
- **my_favorite_skills.txt**: List of skills to download (one per line)
- **download_config.json**: Optional custom download settings

### Core Library (`oreilly_books/`)
- **core.py**: Main `OreillyBooks` class that orchestrates downloads
- **auth.py**: `AuthManager` for cookie-based authentication
- **download.py**: `BookDownloader` for fetching book content
- **epub_legacy.py**: Generates EPUB 2.0 files
- **epub_enhanced.py**: Generates enhanced EPUB 3.3 files (with Kindle support)
- **display.py**: `Display` class for logging and user interface

### Parsers (`oreilly_parser/`)
- **oreilly_books_parser.py**: Searches O'Reilly API, parses book metadata
- **oreilly_skills_parser.py**: Discovers available skills on platform

### Output Directories
- **book_ids/**: JSON files with book metadata per skill
- **books_by_skills/**: Downloaded EPUB files organized by skill folders
- **logs/**: All execution logs (isolated from main directory)
- **output/**: Progress files and result summaries (isolated from main directory)

### Documentation (`docs/`)
All documentation and guides are kept in the docs folder to keep the root clean.

## Data Flow

```
1. User provides cookies.json
         ↓
2. discover_book_ids.py
   - Reads: my_favorite_skills.txt
   - Writes: book_ids/*.json
   - Logs: logs/*.log
   - Progress: output/discovery_progress.json
         ↓
3. download_books.py
   - Reads: book_ids/*.json
   - Writes: books_by_skills/*
   - Logs: logs/*.log
   - Progress: output/download_progress.json
   - Results: output/download_results.json
```

## Clean Separation

### Root Directory (minimal)
- Only essential files: main scripts, README, requirements
- No logs or temp files
- No generated .md documentation

### logs/ Directory
- All .log files
- Automatically created when needed
- Can be safely deleted/cleaned

### output/ Directory
- Progress files (.json)
- Result summaries (.json)
- Can be safely deleted (progress will restart)

### docs/ Directory
- All documentation (.md files)
- Guides and troubleshooting
- Keeps root clean

This structure ensures:
- Clean root directory
- Easy to find logs and output
- Clear separation of concerns
- No clutter from generated files

