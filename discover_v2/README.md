# O'Reilly Book Discovery - V2 API (No Authentication)

This is a modernized version of the book discovery script that uses O'Reilly's v2 API, which **does not require authentication**.

## Key Differences from V1

### Advantages
- ✅ **No authentication required** - No need for cookies.json
- ✅ **More reliable** - Public API endpoint
- ✅ **Better pagination** - 0-based pagination with `next` indicator
- ✅ **Higher limits** - Up to 100 results per page
- ✅ **Cleaner API** - Better structured responses

### API Details

**Endpoint:** `https://learning.oreilly.com/api/v2/search/`

**Parameters:**
- `query=*` - Universal query to get all results
- `topics=<skill_name>` - Filter by skill/topic
- `formats=book` - Only return books
- `limit=100` - Results per page (max 100)
- `page=0` - Page number (0-based)

**Response Structure:**
```json
{
  "results": [...],
  "total": 27,
  "page": 0,
  "next": null,
  "previous": null
}
```

## Usage

### Basic Discovery

Discover all skills:
```bash
cd discover_v2
python3 discover_book_ids_v2.py --skills-source all
```

### Discover Specific Skills

```bash
python3 discover_book_ids_v2.py --skills "Python" "Machine Learning" "Engineering Leadership"
```

### High-Performance Mode

Use multiple workers for parallel discovery:
```bash
python3 discover_book_ids_v2.py --workers 5
```

### Update Mode

Re-discover already discovered skills:
```bash
python3 discover_book_ids_v2.py --update
```

### Dry Run

See what would be discovered without actually running:
```bash
python3 discover_book_ids_v2.py --skills-source favorites --dry-run
```

### Verbose Mode

Get detailed logging:
```bash
python3 discover_book_ids_v2.py --verbose
```

## Configuration

You can customize the discovery process using a config file:

```bash
python3 discover_book_ids_v2.py --config my_config.json
```

See `config.json` for available options.

### Skills File Formats

The script supports two skills file formats:

**Format 1: With Book Counts** (`favorite_skills_with_counts.json`)
```json
{
  "skills": [
    {"title": "Python", "books": 666},
    {"title": "Machine Learning", "books": 958}
  ]
}
```
- Includes expected book counts
- Allows validation against expected numbers
- Default configuration

**Format 2: Simple List** (`skills_facets.json`)
```json
{
  "Python": "Python",
  "Machine Learning": "Machine Learning"
}
```
- Simple key-value pairs
- No expected counts
- Use with: `--config config_skills_facets.json`

Both formats work identically for discovery, only difference is reporting.

## Output

The script generates the following:

1. **book_ids/** - Individual JSON files for each skill
   - Format: `<skill_name>_books.json`
   - Contains all book metadata

2. **discovery_results_v2.json** - Complete results for all skills
   - Includes success/failure statistics
   - Book counts per skill

3. **discovery_summary_v2.txt** - Human-readable summary
   - Top skills by book count
   - Overall statistics

4. **output/discovery_progress.json** - Progress tracking
   - Allows resuming interrupted discoveries
   - Tracks failed skills for retry

5. **book_id_discovery_v2.log** - Detailed log file

## Validation Rules

The script applies the same strict validation rules as v1:

### ✅ Included
- Books in English
- Books with valid ISBNs (or legitimate books without ISBNs)
- Books with meaningful titles (>10 characters)

### ❌ Excluded
- Videos, courses, audiobooks
- Chapters, sections, appendices
- Non-English content
- Duplicates
- Short/invalid titles

## Progress & Resume

The script automatically saves progress and can resume from interruptions:

- Progress is saved after each skill
- Use Ctrl+C to interrupt safely
- Simply re-run the script to resume

## Comparison with V1

| Feature | V1 API | V2 API |
|---------|--------|--------|
| Authentication | Required (cookies) | Not Required |
| Pagination | 1-based | 0-based |
| Results per page | ~15 | Up to 100 |
| Reliability | Medium | High |
| Speed | Slower | Faster |
| Output Format | Same | Same |

## Requirements

```bash
pip install requests
```

No authentication setup needed!

## Troubleshooting

### No results for a skill
- Check if the skill name is exact
- Try variations of the skill name
- Some skills may have 0 books

### API errors
- The v2 API is public and should always work
- Check your internet connection
- Reduce `--workers` if getting rate limited

## Examples

### Discover Engineering Leadership books:
```bash
python3 discover_book_ids_v2.py --skills "Engineering Leadership" --verbose
```

### Quick test with specific skills:
```bash
python3 discover_book_ids_v2.py --skills "Python" "Go" "Rust" --workers 3
```

### Update all skills with verbose output:
```bash
python3 discover_book_ids_v2.py --update --verbose --workers 4
```


