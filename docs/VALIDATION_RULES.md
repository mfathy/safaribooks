# Book Discovery Validation Rules

## Overview
The `discover_book_ids.py` script implements strict validation to ensure only legitimate books are discovered, filtering out videos, courses, audiobooks, chapters, and non-English content.

## Validation Rules

### 1. Format Validation ✅
**Purpose:** Only accept books, skip all other content types

**Accepted formats:**
- `book`
- `ebook`
- `""` (empty, often indicates book)

**Filtered out:**
- `video`
- `course`
- `audiobook`
- `live-training`
- `case-study`
- Any other non-book format

### 2. Language Validation ✅
**Purpose:** English books only

**Accepted:**
- `en`
- `english`
- `""` (empty, assume English)

**Filtered out:**
- All non-English languages (es, fr, de, etc.)

### 3. Title Length Validation ✅
**Purpose:** Filter out incomplete or invalid entries

**Rules:**
- Minimum title length: **10 characters**
- Titles ≤ 5 characters that are only digits: **rejected**

### 4. Chapter & Non-Book Content Validation ✅
**Purpose:** Exclude book fragments and supplementary content

**Filtered keywords:**
- **Chapters:** chapter, part, section, lesson, unit, module
- **Numbered chapters:** chapter 1-10:, part i-v:, section 1-5:, etc.
- **Study materials:** exam ref, certification, study guide, practice test
- **Supplementary:** appendix, glossary, index, bibliography
- **Front/back matter:** introduction, preface, foreword, acknowledgments, conclusion, summary, wrap-up

### 5. ISBN Validation ✅
**Purpose:** Prefer books with valid ISBNs

**Rules:**
- Books **with ISBN**: Accepted ✅
- Books **without ISBN**: 
  - If title contains: chapter, video, course, tutorial, workshop, webinar, audiobook → **Rejected**
  - If title < 15 characters → **Rejected**
  - Otherwise → Accepted with warning ⚠️

**Invalid ISBN values:**
- Empty string
- "n/a"
- "none"
- "null"

### 6. Numbered Item Validation ✅
**Purpose:** Filter out numbered chapter/section entries

**Rules:**
- If title starts with a digit AND is simple format (≤3 words, contains "." or ≤2 spaces)
  - Example: "1. Introduction", "2 Overview"
  - Action: **Rejected**
- Complex numbered titles are kept:
  - Example: "3D Data Science", "2001: A Space Odyssey"
  - Action: **Accepted**

### 7. Duplicate Detection ✅
**Purpose:** Prevent duplicate books

**Method:**
- Track unique book IDs (archive_id, isbn, ourn)
- Skip if already seen in current skill

## Filtering Statistics

The script logs detailed statistics after each skill:

```
📊 Filtering Results:
   📚 Total books found: 30
   📖 Books with ISBN: 30
   📝 Books without ISBN: 0
   ⏭️  Filtered out: videos, chapters, courses, non-English content
```

## Examples

### ✅ Accepted Books
- "The Staff Engineer's Path" (book with ISBN)
- "Engineering Leadership: The Hard Parts" (book with ISBN)
- "Think Like a Software Engineering Manager" (book with ISBN)

### ❌ Filtered Out
- "Chapter 1: Introduction to Leadership" (chapter keyword)
- "Leadership Video Course" (video format)
- "Leadership Tutorial" (tutorial keyword)
- "Engineering Leadership Webinar" (webinar keyword)
- "1. Introduction" (numbered item)
- Short titles < 10 characters

## Impact

**Engineering Leadership Example:**
- Before validation: 60 items
- After validation: 30 books
- **Filtered out: 30 non-book items (50%)**

This ensures:
1. Only downloadable books are included
2. No duplicate downloads
3. Better compatibility with download tools
4. Higher quality book collection

## Validation Logging

In **verbose mode** (`--verbose`), the script logs each validation decision:

```bash
python3 discover_book_ids.py --skills "Engineering Leadership" --verbose
```

Sample output:
```
⏭️  Skipping video: Engineering Leadership Fundamentals
⏭️  Skipping chapter/section: Chapter 1: Introduction
⏭️  Skipping no ISBN (likely chapter/video/course): Leadership Quick Tips
✅ Added book: The Staff Engineer's Path
⚠️  Book without ISBN (keeping): Modern Engineering Leadership
```

## Configuration

All validation rules are **hardcoded** for consistency and cannot be disabled. This ensures:
- Predictable behavior across all runs
- High-quality book collections
- No accidental inclusion of non-book content

## Date
October 17, 2025

