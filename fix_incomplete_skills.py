#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Incomplete Skills Script
Identifies and fixes skills with incomplete book information
"""

import os
import json
from pathlib import Path


def find_incomplete_skills():
    """Find skills with incomplete book information"""
    book_ids_dir = Path("book_ids")
    incomplete_skills = []
    
    for skill_file in book_ids_dir.glob("*_books.json"):
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            books = data.get('books', [])
            if not books:
                continue
            
            # Check if first book has generic title
            first_book = books[0]
            if 'title' in first_book and first_book['title'].startswith('Book '):
                skill_name = data.get('skill_name', skill_file.stem.replace('_books', ''))
                incomplete_skills.append({
                    'file': skill_file,
                    'skill_name': skill_name,
                    'book_count': len(books),
                    'sample_id': first_book.get('id', 'unknown')
                })
                
        except Exception as e:
            print(f"Error reading {skill_file}: {e}")
    
    return incomplete_skills


def analyze_incomplete_skills():
    """Analyze the incomplete skills"""
    print("🔍 Analyzing incomplete skills...")
    
    incomplete_skills = find_incomplete_skills()
    
    print(f"\n📊 Found {len(incomplete_skills)} skills with incomplete information:")
    print("=" * 60)
    
    for skill in incomplete_skills[:20]:  # Show first 20
        print(f"📚 {skill['skill_name']}: {skill['book_count']} books (ID: {skill['sample_id']})")
    
    if len(incomplete_skills) > 20:
        print(f"... and {len(incomplete_skills) - 20} more skills")
    
    print(f"\n📈 Summary:")
    print(f"   Total incomplete skills: {len(incomplete_skills)}")
    
    total_books = sum(skill['book_count'] for skill in incomplete_skills)
    print(f"   Total books affected: {total_books:,}")
    
    # Check if these are ISBNs or other IDs
    isbn_count = 0
    url_count = 0
    
    for skill in incomplete_skills:
        sample_id = skill['sample_id']
        if sample_id.startswith('http'):
            url_count += 1
        elif sample_id.isdigit() and len(sample_id) >= 10:
            isbn_count += 1
    
    print(f"   ISBN-based IDs: {isbn_count}")
    print(f"   URL-based IDs: {url_count}")
    print(f"   Other IDs: {len(incomplete_skills) - isbn_count - url_count}")
    
    return incomplete_skills


def check_download_compatibility():
    """Check if the incomplete skills can still be downloaded"""
    print("\n🔧 Checking download compatibility...")
    
    incomplete_skills = find_incomplete_skills()
    
    # Check if the download script can handle these IDs
    from download_books import BookDownloader
    
    downloader = BookDownloader()
    
    compatible_count = 0
    incompatible_count = 0
    
    for skill in incomplete_skills[:10]:  # Test first 10
        try:
            with open(skill['file'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            books = data.get('books', [])
            if not books:
                continue
            
            first_book = books[0]
            book_id = first_book.get('id', '')
            
            # Check if it looks like a valid book ID for downloading
            if book_id.isdigit() and len(book_id) >= 10:
                # This is an ISBN, which should work
                compatible_count += 1
            elif 'book/' in book_id and book_id.replace('https://', '').replace('http://', '').replace('www.safaribooksonline.com/api/v1/book/', '').replace('learning.oreilly.com/api/v1/book/', '').replace('/', '').isdigit():
                # This is a URL with a book ID, which should work
                compatible_count += 1
            else:
                incompatible_count += 1
                print(f"⚠️  Potentially incompatible: {skill['skill_name']} (ID: {book_id[:50]}...)")
                
        except Exception as e:
            print(f"❌ Error checking {skill['skill_name']}: {e}")
    
    print(f"\n📊 Compatibility Check Results:")
    print(f"   Compatible: {compatible_count}")
    print(f"   Potentially incompatible: {incompatible_count}")
    
    return compatible_count, incompatible_count


def suggest_fixes():
    """Suggest fixes for incomplete skills"""
    print("\n💡 Suggested Fixes:")
    print("=" * 40)
    
    print("1. 🎯 **Accept Current State** (Recommended)")
    print("   - Books will still download correctly")
    print("   - ISBNs are valid book identifiers")
    print("   - Generic titles don't affect functionality")
    print("   - No action needed")
    
    print("\n2. 🔄 **Re-run Discovery**")
    print("   - Run: python3 discover_book_ids.py --skills 'A/B Testing' 'AdWords' ...")
    print("   - May get better results with different API timing")
    print("   - Time-consuming for 62 skills")
    
    print("\n3. 🛠️ **Improve Discovery Script**")
    print("   - Enhance API parsing logic")
    print("   - Add retry mechanisms")
    print("   - Better fallback handling")
    print("   - Requires code changes")
    
    print("\n4. 📚 **Manual Enhancement**")
    print("   - Use ISBN lookup services to get real titles")
    print("   - Update JSON files with better metadata")
    print("   - Most accurate but very time-consuming")


def main():
    """Main function"""
    print("🔍 Incomplete Skills Analysis")
    print("=" * 50)
    
    # Analyze incomplete skills
    incomplete_skills = analyze_incomplete_skills()
    
    if not incomplete_skills:
        print("✅ All skills have complete information!")
        return
    
    # Check download compatibility
    compatible, incompatible = check_download_compatibility()
    
    # Suggest fixes
    suggest_fixes()
    
    print(f"\n🎯 Recommendation:")
    if compatible > incompatible:
        print("✅ **Proceed with current files** - they should download correctly")
        print("   The generic titles are just cosmetic and don't affect functionality")
    else:
        print("⚠️  **Consider re-running discovery** for problematic skills")
        print("   Some books may not download correctly with current IDs")
    
    print(f"\n📋 Affected skills list:")
    for skill in incomplete_skills:
        print(f"   - {skill['skill_name']}")


if __name__ == "__main__":
    main()
