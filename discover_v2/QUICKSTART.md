# Quick Start Guide - V2 Discovery System

## 🚀 No Authentication Required!

The V2 API doesn't require any authentication setup. Just run and go!

## Quick Test (Single Skill)

Test with one skill to verify everything works:

```bash
cd discover_v2
python3 discover_book_ids_v2.py --skills "Engineering Leadership"
```

**Expected output:** ~25-27 books discovered in seconds

## Discover All Skills

Discover all 286 skills from your favorite list:

```bash
python3 discover_book_ids_v2.py
```

**Note:** This will:
- Skip already discovered skills (resume support)
- Process ~286 skills
- Take several hours to complete
- Save progress automatically

## Common Use Cases

### 1. Discover Specific Topics

```bash
python3 discover_book_ids_v2.py --skills "Python" "Machine Learning" "Data Science"
```

### 2. Parallel Discovery (Faster)

Use multiple workers for faster discovery:

```bash
python3 discover_book_ids_v2.py --workers 5
```

### 3. Update Existing Skills

Re-discover skills that were already discovered:

```bash
python3 discover_book_ids_v2.py --update
```

### 4. Verbose Mode (Debugging)

See detailed logs of what's happening:

```bash
python3 discover_book_ids_v2.py --skills "Python" --verbose
```

### 5. Dry Run (Preview)

See what would be discovered without actually running:

```bash
python3 discover_book_ids_v2.py --dry-run
```

## Output Files

After running, you'll find:

```
discover_v2/
├── book_ids/
│   ├── engineering_leadership_books.json
│   ├── python_books.json
│   └── ... (one file per skill)
├── discovery_results_v2.json          # Complete results
├── discovery_summary_v2.txt           # Human-readable summary
├── output/
│   └── discovery_progress.json        # Progress tracking
└── book_id_discovery_v2.log          # Detailed logs
```

## Resume Support

The script automatically saves progress. If interrupted:

1. Press `Ctrl+C` to stop
2. Run the same command again
3. It will skip already discovered skills and continue

## Customization

Edit `config.json` to customize:

- `max_workers`: Number of parallel threads (default: 3)
- `discovery_delay`: Delay between skills in seconds (default: 1)
- `priority_skills`: Skills to discover first
- `exclude_skills`: Skills to skip

## Comparison with V1

| Feature | V1 | V2 |
|---------|----|----|
| Authentication | Required | Not Required ✅ |
| Speed | Slower | Faster ✅ |
| Reliability | Good | Better ✅ |
| Results per page | ~15 | 100 ✅ |
| Output format | JSON | JSON (same) |

## Troubleshooting

### No results for a skill
- The skill name must match exactly
- Check spelling and capitalization
- Some skills may have 0 books

### Rate limiting
- Reduce `--workers` to 1 or 2
- Increase delay in config.json

### Connection errors
- Check internet connection
- The API should always be available (no auth required)

## Next Steps

After discovery, use the book IDs to:
1. Download books using the main download script
2. Organize by skills
3. Build your personal O'Reilly library

## Support

Check the logs for detailed information:
```bash
tail -f book_id_discovery_v2.log
```

Or view the summary:
```bash
cat discovery_summary_v2.txt
```

