# File Index - V2 Discovery System

Complete list of all files in the v2 discovery system and their purposes.

## 📄 Core Files

### `discover_book_ids_v2.py` (32KB)
**Purpose:** Main discovery script using O'Reilly v2 API

**Key Features:**
- No authentication required
- Parallel discovery support
- Progress tracking & resume
- All validation rules from v1
- Same output format as v1

**Usage:**
```bash
python3 discover_book_ids_v2.py [--skills SKILL1 SKILL2] [--workers N] [--verbose]
```

### `config.json` (561B)
**Purpose:** Configuration file for customizing discovery behavior

**Key Settings:**
- `max_workers`: Parallel threads (default: 3)
- `discovery_delay`: Delay between skills (default: 1s)
- `priority_skills`: Skills to discover first
- `exclude_skills`: Skills to skip
- `skills_file`: Path to skills list

**Edit to customize your discovery process**

## 📚 Documentation Files

### `README.md` (4.0KB)
**Purpose:** Complete documentation and user guide

**Contents:**
- API details and parameters
- Usage examples
- Configuration options
- Output file descriptions
- Validation rules
- Troubleshooting guide
- Comparison table with v1

**Read this first for complete understanding**

### `QUICKSTART.md` (3.2KB)
**Purpose:** Quick start guide for immediate use

**Contents:**
- No-setup quick test
- Common use cases with examples
- Output file locations
- Resume support instructions
- Quick troubleshooting

**Best for getting started quickly**

### `COMPARISON.md` (5.0KB)
**Purpose:** Detailed comparison between v1 and v2 APIs

**Contents:**
- Authentication differences
- API endpoint comparison
- Response structure comparison
- Performance benchmarks
- Feature parity table
- Migration guide
- When to use which version

**Best for understanding differences from v1**

### `V2_SUMMARY.md` (7.2KB)
**Purpose:** Complete summary of the v2 system

**Contents:**
- What was created
- Key features
- API details
- Usage examples
- Configuration options
- Test results
- Advantages over v1
- Recommended workflow

**Best for overall understanding**

### `FILE_INDEX.md` (This file)
**Purpose:** Index of all files with descriptions

## 📊 Output Files

### `book_ids/` (directory)
**Purpose:** Stores individual JSON files for each discovered skill

**File Format:** `<skill_name>_books.json`

**Example:** `engineering_leadership_books.json`

**Content Structure:**
```json
{
  "skill_name": "Engineering Leadership",
  "discovery_timestamp": 1234567890.123,
  "total_books": 25,
  "books": [...]
}
```

### `discovery_results_v2.json` (8.7KB)
**Purpose:** Complete results for all discovered skills

**Contents:**
- Skills processed count
- Total books discovered
- Success/failure statistics
- Detailed results per skill
- Error messages for failed skills

**Use for:** Overall analysis and statistics

### `discovery_summary_v2.txt` (427B)
**Purpose:** Human-readable summary of discovery results

**Contents:**
- Skills processed
- Books discovered
- Top skills by book count
- Quick statistics

**Use for:** Quick overview and sharing results

### `output/discovery_progress.json`
**Purpose:** Progress tracking for resume support

**Contents:**
- List of discovered skills
- Failed skills with error messages
- Timestamp

**Use for:** Resume interrupted discoveries

### `book_id_discovery_v2.log` (3.0KB)
**Purpose:** Detailed log of all operations

**Contents:**
- INFO: Progress messages
- DEBUG: Detailed operations (with --verbose)
- WARNING: Issues encountered
- ERROR: Failed operations

**Use for:** Debugging and troubleshooting

## 📁 Directory Structure

```
discover_v2/
├── Core Files
│   ├── discover_book_ids_v2.py    # Main script
│   └── config.json                 # Configuration
│
├── Documentation
│   ├── README.md                   # Complete docs
│   ├── QUICKSTART.md              # Quick start
│   ├── COMPARISON.md              # V1 vs V2
│   ├── V2_SUMMARY.md              # Summary
│   └── FILE_INDEX.md              # This file
│
├── Output
│   ├── book_ids/                  # Individual skill files
│   ├── discovery_results_v2.json  # Complete results
│   ├── discovery_summary_v2.txt   # Summary
│   └── output/
│       └── discovery_progress.json # Progress tracking
│
└── Logs
    └── book_id_discovery_v2.log   # Detailed logs
```

## 🎯 File Purposes by Use Case

### To Get Started:
1. Read `QUICKSTART.md`
2. Edit `config.json` (optional)
3. Run `discover_book_ids_v2.py`

### To Understand the System:
1. Read `V2_SUMMARY.md`
2. Read `README.md`
3. Check `COMPARISON.md` (if coming from v1)

### To Use the Results:
1. Check `discovery_summary_v2.txt` for overview
2. Browse `book_ids/` for individual skill files
3. Read `discovery_results_v2.json` for complete data

### To Debug Issues:
1. Check `book_id_discovery_v2.log`
2. Run with `--verbose` flag
3. Check `output/discovery_progress.json`

### To Resume Discovery:
1. Just run the script again
2. It reads `output/discovery_progress.json`
3. Skips already discovered skills

## 📈 File Sizes (Typical)

| File | Size | After Full Discovery |
|------|------|---------------------|
| discover_book_ids_v2.py | 32KB | 32KB (static) |
| config.json | 561B | 561B (static) |
| discovery_results_v2.json | ~10KB | ~500KB - 1MB |
| discovery_summary_v2.txt | ~500B | ~5KB |
| book_id_discovery_v2.log | ~3KB | ~100KB - 500KB |
| book_ids/ | - | ~10MB - 50MB |
| output/discovery_progress.json | ~1KB | ~50KB |

## 🔄 File Lifecycle

### Before Running:
- `discover_book_ids_v2.py` ✅ (provided)
- `config.json` ✅ (provided)
- Documentation files ✅ (provided)

### During Discovery:
- `book_id_discovery_v2.log` - Being written
- `output/discovery_progress.json` - Updated after each skill
- `book_ids/<skill>.json` - Created per skill

### After Completion:
- `discovery_results_v2.json` - Created
- `discovery_summary_v2.txt` - Created
- All book_ids/ files complete
- Progress file final state

## 🎨 File Formats

### Python Script: `.py`
- UTF-8 encoded
- Executable permission set
- Shebang: `#!/usr/bin/env python3`

### JSON Files: `.json`
- Pretty-printed with 2-space indent
- UTF-8 encoded
- No ASCII escaping

### Markdown Files: `.md`
- UTF-8 encoded
- GitHub-flavored markdown
- Code blocks with syntax highlighting

### Text Files: `.txt`
- UTF-8 encoded
- Plain text format
- Unix line endings

### Log Files: `.log`
- UTF-8 encoded
- Standard Python logging format
- Timestamped entries

## 📝 Notes

1. **All files are UTF-8 encoded** - Support for international characters
2. **JSON files use indent=2** - Human-readable formatting
3. **Logs rotate if large** - Configured in script
4. **Progress files are safe** - Atomic writes to prevent corruption
5. **Output format matches v1** - Full compatibility

## 🔗 Quick Links

- Main script: `discover_book_ids_v2.py`
- Quick start: `QUICKSTART.md`
- Full docs: `README.md`
- V1 comparison: `COMPARISON.md`
- Complete summary: `V2_SUMMARY.md`
- This index: `FILE_INDEX.md`

---

**Last Updated:** October 18, 2025  
**Version:** 2.0  
**Status:** Production Ready ✅












