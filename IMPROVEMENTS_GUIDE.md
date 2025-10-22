# O'Reilly Book Downloader - Improvements Quick Reference

## 🎯 What's New

### 1. Token Refresh Fix ✅
**Problem Solved:** Books were failing with JSON parse errors after a few downloads.

**How It Works:** Cookies are now automatically updated after EVERY HTTP request, keeping authentication fresh indefinitely.

**No Action Needed:** This works automatically in the background.

---

### 2. Smart EPUB Detection ✅
**What Changed:** The script now checks if EPUB files actually exist on disk before downloading.

**Benefits:**
- More reliable skip logic
- Works even if progress file is corrupted
- Respects different EPUB formats (legacy, enhanced, kindle, dual)

**Example:**
```bash
# First run: Downloads books
python3 download_books.py --skills "Python" --max-books 5

# Second run: Skips books (EPUB files exist)
python3 download_books.py --skills "Python" --max-books 5
# Output: ⏭️ Skipping <book> (EPUB already exists)
```

---

### 3. Force Redownload Option ✅
**Use Case:** Update existing books with new versions or corrections.

**How to Use:**

**Command Line:**
```bash
# Force re-download all books
python3 download_books.py --force

# Force re-download specific skills
python3 download_books.py --skills "Python" "Machine Learning" --force
```

**Interactive Mode:**
```bash
python3 quick_download.py
# Select option 5: "Force re-download all books (updates existing)"
```

**Configuration File:**
```json
{
  "force_redownload": true
}
```

---

### 4. Configurable Token Refresh ✅
**What It Does:** Controls how often authentication cookies are saved to disk.

**Default:** Every 5 books (recommended)

**How to Change:**

**Command Line:**
```bash
# Save tokens more frequently (every 2 books)
python3 download_books.py --token-save-interval 2

# Save tokens less frequently (every 10 books)
python3 download_books.py --token-save-interval 10
```

**Configuration File:**
```json
{
  "token_save_interval": 5
}
```

**When to Adjust:**
- **Lower (2-3)**: If you experience occasional authentication errors
- **Default (5)**: Good for most users
- **Higher (10+)**: If tokens are stable and you want fewer disk writes

---

## 📋 Quick Commands

### Standard Download (Recommended)
```bash
# Download all discovered books, skip existing
python3 download_books.py
```

### Download Specific Skills
```bash
python3 download_books.py --skills "Python" "Machine Learning" "AI & ML"
```

### Update Existing Books
```bash
# Re-download everything (overwrites existing EPUBs)
python3 download_books.py --force
```

### Conservative Token Refresh
```bash
# Save tokens frequently (good if you have token issues)
python3 download_books.py --token-save-interval 2
```

### Custom Download
```bash
# All options combined
python3 download_books.py \
  --skills "Python" "Data Science" \
  --max-books 20 \
  --format dual \
  --token-save-interval 3 \
  --verbose
```

### Interactive Mode (Easiest)
```bash
python3 quick_download.py
```

**New Options in Interactive Mode:**
- Option 5: Force re-download all books
- Option 6: Custom configuration (now includes force and token settings)

---

## 🔧 Configuration File Reference

**File:** `download_config.json`

```json
{
  "base_directory": "books",
  "book_ids_directory": "book_ids",
  "max_books_per_skill": 100,
  "download_delay": 10,
  "epub_format": "dual",
  "resume": true,
  
  // NEW OPTIONS
  "force_redownload": false,      // Set true to update existing books
  "token_save_interval": 5,       // Save cookies after N books
  
  "progress_file": "download_progress.json",
  "verbose": true
}
```

---

## 📊 Download Behavior

### Without --force (Default)
```
Book 1: ✅ Downloaded (EPUB doesn't exist)
Book 2: ⏭️  Skipped (EPUB already exists)
Book 3: ✅ Downloaded (EPUB doesn't exist)
Book 4: ⏭️  Skipped (Already in progress tracker)
```

### With --force
```
Book 1: 🔄 Force re-downloading (overwrites existing EPUB)
Book 2: 🔄 Force re-downloading (overwrites existing EPUB)
Book 3: 🔄 Force re-downloading (overwrites existing EPUB)
Book 4: 🔄 Force re-downloading (overwrites existing EPUB)
```

---

## 🎓 Best Practices

### First Time Download
```bash
# Use defaults - they work great
python3 download_books.py
```

### Updating Your Library
```bash
# Force re-download books that may have been updated
python3 download_books.py --force
```

### Experiencing Token Issues?
```bash
# Save tokens more frequently
python3 download_books.py --token-save-interval 2 --verbose

# Check logs for cookie updates
grep "Saved authentication cookies" logs/book_downloader.log
```

### Large Library Download
```bash
# Default settings are optimized for large downloads
python3 download_books.py --max-books 100

# Tokens refresh automatically after every HTTP request
# Cookies saved to disk every 5 books by default
```

---

## 🐛 Troubleshooting

### "Expecting value: line 1 column 1 (char 0)" Error
**This should no longer happen!** The token refresh fix prevents this.

If you still see it:
1. Refresh your `cookies.json` file
2. Lower token save interval: `--token-save-interval 2`
3. Check logs: `grep "Updated cookie" logs/book_downloader.log`

### Books Re-downloading When They Shouldn't
1. Verify `--force` flag is NOT being used
2. Check config: `"force_redownload": false`
3. Ensure EPUB files contain the book ID in their filename

### Force Redownload Not Working
1. Confirm `--force` flag is present
2. Look for "Force re-downloading:" in logs
3. Try command line instead of config file

---

## 📈 What You'll See in Logs

### Normal Download
```
📚 Downloading: Python Tricks (ID: 9781775093301)
💾 Saved authentication cookies (keeps tokens fresh)
✅ Successfully downloaded: Python Tricks
```

### Skipping Existing
```
⏭️  Skipping Python Tricks (EPUB already exists)
```

### Force Redownload
```
🔄 Force re-downloading: Python Tricks
📚 Downloading: Python Tricks (ID: 9781775093301)
✅ Successfully downloaded: Python Tricks
```

### Token Refresh (Debug Mode)
```
DEBUG - Updated cookie: session_id
DEBUG - Updated cookie: csrf_token
INFO - 💾 Saved authentication cookies (keeps tokens fresh)
```

---

## ✅ Summary

**Token Issues:** ✅ Fixed - automatic refresh after every request  
**EPUB Detection:** ✅ Improved - checks actual files on disk  
**Force Update:** ✅ Added - can re-download existing books  
**Token Saves:** ✅ Configurable - adjust to your needs  
**User Interface:** ✅ Enhanced - more options in quick_download.py  

**Just run:**
```bash
python3 download_books.py
```

Everything else works automatically! 🎉

