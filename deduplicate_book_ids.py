#!/usr/bin/env python3
"""
Deduplicate Book IDs Across Skill Files

This script removes duplicate book IDs across all JSON files in the book_ids directory,
keeping only the first occurrence of each book based on alphabetical file order.
"""

import json
import os
import shutil
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def load_json_file(file_path):
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def save_json_file(file_path, data):
    """Save data to a JSON file with proper formatting."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        return False

def create_backup(book_ids_dir, backup_dir):
    """Create a backup of all JSON files."""
    print(f"Creating backup in {backup_dir}...")
    os.makedirs(backup_dir, exist_ok=True)
    
    json_files = list(Path(book_ids_dir).glob("*.json"))
    for file_path in json_files:
        backup_path = Path(backup_dir) / file_path.name
        shutil.copy2(file_path, backup_path)
    
    print(f"Backup created: {len(json_files)} files backed up")
    return len(json_files)

def create_timestamped_backups():
    """Create timestamped backups of all source directories."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dirs = {}
    
    # Define source directories and their backup names
    sources = {
        'main': ('/Users/mohammed/Work/oreilly-books/book_ids', f'book_ids_backup_{timestamp}'),
        'discover_v2': ('/Users/mohammed/Work/oreilly-books/discover_v2/book_ids', f'discover_v2_backup_{timestamp}'),
        'discover_by_page': ('/Users/mohammed/Work/oreilly-books/discover_by_page/book_ids', f'discover_by_page_backup_{timestamp}')
    }
    
    print("Creating timestamped backups...")
    for source_name, (source_dir, backup_name) in sources.items():
        if os.path.exists(source_dir):
            backup_path = f"/Users/mohammed/Work/oreilly-books/{backup_name}"
            file_count = create_backup(source_dir, backup_path)
            backup_dirs[source_name] = backup_path
            print(f"  {source_name}: {file_count} files backed up to {backup_path}")
        else:
            print(f"  {source_name}: Directory {source_dir} not found, skipping backup")
            backup_dirs[source_name] = None
    
    return backup_dirs

def merge_book_entries(book1, book2):
    """Merge two book entries, keeping the most complete one."""
    # Count non-empty fields in each book
    def count_fields(book):
        return sum(1 for v in book.values() if v and v != "")
    
    # If one has significantly more fields, use it
    if count_fields(book1) > count_fields(book2) + 2:
        return book1
    elif count_fields(book2) > count_fields(book1) + 2:
        return book2
    
    # Otherwise, prefer the one with more important fields
    important_fields = ['main_topic', 'secondary_topics', 'description', 'authors', 'publisher']
    book1_score = sum(1 for field in important_fields if book1.get(field))
    book2_score = sum(1 for field in important_fields if book2.get(field))
    
    if book1_score > book2_score:
        return book1
    elif book2_score > book1_score:
        return book2
    
    # If scores are equal, merge fields, preferring non-empty values
    merged = book1.copy()
    for key, value in book2.items():
        if key not in merged or not merged[key] or merged[key] == "":
            if value and value != "":
                merged[key] = value
        elif isinstance(value, list) and isinstance(merged[key], list):
            # Merge lists, removing duplicates
            merged[key] = list(set(merged[key] + value))
    
    return merged

def merge_all_sources():
    """Merge books from all source directories into the main book_ids directory."""
    print("Starting merge of all source directories...")
    
    # Define source directories in processing order
    source_dirs = [
        ('/Users/mohammed/Work/oreilly-books/book_ids_backup', 'backup'),
        ('/Users/mohammed/Work/oreilly-books/discover_by_page/book_ids', 'discover_by_page'),
        ('/Users/mohammed/Work/oreilly-books/discover_v2/book_ids', 'discover_v2')
    ]
    
    main_dir = '/Users/mohammed/Work/oreilly-books/book_ids'
    os.makedirs(main_dir, exist_ok=True)
    
    # Track statistics
    merge_stats = {
        'skills_processed': 0,
        'books_merged': 0,
        'new_skills_added': 0,
        'books_enhanced': 0,
        'source_breakdown': {}
    }
    
    # Get all unique skill files across all sources
    all_skill_files = set()
    for source_dir, source_name in source_dirs:
        if os.path.exists(source_dir):
            json_files = list(Path(source_dir).glob("*.json"))
            for file_path in json_files:
                all_skill_files.add(file_path.name)
            merge_stats['source_breakdown'][source_name] = len(json_files)
    
    print(f"Found {len(all_skill_files)} unique skill files across all sources")
    
    # Process each skill file
    for skill_file in sorted(all_skill_files):
        print(f"Processing skill: {skill_file}")
        merge_stats['skills_processed'] += 1
        
        # Collect all versions of this skill file from all sources
        skill_versions = []
        for source_dir, source_name in source_dirs:
            if os.path.exists(source_dir):
                file_path = Path(source_dir) / skill_file
                if file_path.exists():
                    data = load_json_file(file_path)
                    if data and 'books' in data:
                        skill_versions.append((data, source_name))
        
        if not skill_versions:
            continue
        
        # Load or create main skill file
        main_file_path = Path(main_dir) / skill_file
        if main_file_path.exists():
            main_data = load_json_file(main_file_path)
            if main_data and 'books' in main_data:
                skill_versions.insert(0, (main_data, 'main'))
            else:
                main_data = None
        else:
            main_data = None
            merge_stats['new_skills_added'] += 1
        
        # Merge all versions
        if main_data:
            merged_books = main_data['books'].copy()
        else:
            # Use the first available version as base
            merged_books = skill_versions[0][0]['books'].copy()
            main_data = skill_versions[0][0].copy()
        
        # Merge books from all sources
        for data, source_name in skill_versions:
            if source_name == 'main':
                continue  # Already included
                
            for book in data['books']:
                book_id = book.get('id')
                if not book_id:
                    continue
                
                # Check if book already exists
                existing_book = None
                for i, existing in enumerate(merged_books):
                    if existing.get('id') == book_id:
                        existing_book = (i, existing)
                        break
                
                if existing_book:
                    # Merge with existing book
                    old_book = existing_book[1]
                    new_book = merge_book_entries(old_book, book)
                    if new_book != old_book:
                        merged_books[existing_book[0]] = new_book
                        merge_stats['books_enhanced'] += 1
                else:
                    # Add new book
                    merged_books.append(book)
                    merge_stats['books_merged'] += 1
        
        # Update main data
        main_data['books'] = merged_books
        main_data['total_books'] = len(merged_books)
        
        # Save merged file
        if save_json_file(main_file_path, main_data):
            print(f"  Merged {len(merged_books)} books for {skill_file}")
        else:
            print(f"  Failed to save {skill_file}")
    
    return merge_stats

def cleanup_source_directories():
    """Delete source directories after successful merge."""
    print("Cleaning up source directories...")
    
    source_dirs = [
        '/Users/mohammed/Work/oreilly-books/book_ids_backup',
        '/Users/mohammed/Work/oreilly-books/discover_by_page/book_ids',
        '/Users/mohammed/Work/oreilly-books/discover_v2/book_ids'
    ]
    
    cleaned_dirs = []
    for source_dir in source_dirs:
        if os.path.exists(source_dir):
            try:
                shutil.rmtree(source_dir)
                cleaned_dirs.append(source_dir)
                print(f"  Deleted: {source_dir}")
            except Exception as e:
                print(f"  Error deleting {source_dir}: {e}")
        else:
            print(f"  Directory not found: {source_dir}")
    
    return cleaned_dirs

def deduplicate_books(book_ids_dir):
    """Main deduplication logic."""
    print("Starting book ID deduplication...")
    
    # Get all JSON files and sort alphabetically
    json_files = sorted(Path(book_ids_dir).glob("*.json"))
    print(f"Found {len(json_files)} JSON files to process")
    
    # Track seen book IDs and their first occurrence
    seen_book_ids = set()
    book_id_to_first_file = {}
    duplicates_removed = defaultdict(int)
    total_duplicates = 0
    
    # Process each file in alphabetical order
    for file_path in json_files:
        print(f"Processing: {file_path.name}")
        
        # Load the file
        data = load_json_file(file_path)
        if not data or 'books' not in data:
            print(f"  Skipping {file_path.name} - invalid format")
            continue
        
        original_count = len(data['books'])
        unique_books = []
        
        # Process each book in the file
        for book in data['books']:
            book_id = book.get('id')
            if not book_id:
                print(f"  Warning: Book without ID found in {file_path.name}")
                continue
            
            if book_id in seen_book_ids:
                # This is a duplicate - remove it
                duplicates_removed[file_path.name] += 1
                total_duplicates += 1
                print(f"  Removed duplicate: {book.get('title', 'Unknown')} (ID: {book_id})")
            else:
                # First time seeing this book ID - keep it
                seen_book_ids.add(book_id)
                book_id_to_first_file[book_id] = file_path.name
                unique_books.append(book)
        
        # Update the data with deduplicated books
        data['books'] = unique_books
        data['total_books'] = len(unique_books)
        
        # Save the updated file
        if save_json_file(file_path, data):
            removed_count = original_count - len(unique_books)
            print(f"  Updated {file_path.name}: {original_count} -> {len(unique_books)} books ({removed_count} duplicates removed)")
        else:
            print(f"  Failed to save {file_path.name}")
    
    return {
        'total_files_processed': len(json_files),
        'total_duplicates_removed': total_duplicates,
        'duplicates_per_file': dict(duplicates_removed),
        'unique_books_total': len(seen_book_ids)
    }

def generate_summary_report(results, merge_stats, output_file):
    """Generate a comprehensive summary report of the merge and deduplication process."""
    report = {
        'merge_and_deduplication_summary': {
            'timestamp': datetime.now().isoformat(),
            'merge_statistics': merge_stats,
            'deduplication_statistics': {
                'total_files_processed': results['total_files_processed'],
                'total_duplicates_removed': results['total_duplicates_removed'],
                'unique_books_total': results['unique_books_total'],
                'duplicates_per_file': results['duplicates_per_file']
            },
            'overall_summary': {
                'total_skills_processed': merge_stats.get('skills_processed', 0),
                'new_skills_added': merge_stats.get('new_skills_added', 0),
                'books_merged_from_sources': merge_stats.get('books_merged', 0),
                'books_enhanced_with_metadata': merge_stats.get('books_enhanced', 0),
                'total_duplicates_removed': results['total_duplicates_removed'],
                'final_unique_books': results['unique_books_total']
            }
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nSummary report saved to: {output_file}")
    return report

def main():
    """Main execution function."""
    book_ids_dir = "/Users/mohammed/Work/oreilly-books/book_ids"
    report_file = "/Users/mohammed/Work/oreilly-books/merge_and_deduplication_report.json"
    
    print("=" * 80)
    print("BOOK ID MERGE AND DEDUPLICATION TOOL")
    print("=" * 80)
    
    # Verify main directory exists
    if not os.path.exists(book_ids_dir):
        print(f"Error: Directory {book_ids_dir} does not exist")
        return
    
    try:
        # Step 1: Create timestamped backups
        print("\n1. Creating timestamped backups...")
        backup_dirs = create_timestamped_backups()
        
        # Step 2: Merge all sources
        print("\n2. Merging books from all source directories...")
        merge_stats = merge_all_sources()
        
        # Step 3: Deduplicate across skills
        print("\n3. Deduplicating books across skills...")
        dedup_results = deduplicate_books(book_ids_dir)
        
        # Step 4: Cleanup source directories
        print("\n4. Cleaning up source directories...")
        cleaned_dirs = cleanup_source_directories()
        
        # Step 5: Generate comprehensive report
        print("\n5. Generating summary report...")
        summary = generate_summary_report(dedup_results, merge_stats, report_file)
        
        # Print final summary
        print("\n" + "=" * 80)
        print("MERGE AND DEDUPLICATION COMPLETE")
        print("=" * 80)
        print(f"Skills processed: {merge_stats['skills_processed']}")
        print(f"New skills added: {merge_stats['new_skills_added']}")
        print(f"Books merged from sources: {merge_stats['books_merged']}")
        print(f"Books enhanced with metadata: {merge_stats['books_enhanced']}")
        print(f"Total duplicates removed: {dedup_results['total_duplicates_removed']}")
        print(f"Final unique books: {dedup_results['unique_books_total']}")
        print(f"Source directories cleaned: {len(cleaned_dirs)}")
        print(f"Summary report: {report_file}")
        
        # Show source breakdown
        if merge_stats.get('source_breakdown'):
            print("\nSource breakdown:")
            for source, count in merge_stats['source_breakdown'].items():
                print(f"  {source}: {count} files")
        
        # Show files with most duplicates removed
        if dedup_results['duplicates_per_file']:
            print("\nTop 10 files with most duplicates removed:")
            sorted_duplicates = sorted(
                dedup_results['duplicates_per_file'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            for filename, count in sorted_duplicates:
                if count > 0:
                    print(f"  {filename}: {count} duplicates removed")
        
        print("\n" + "=" * 80)
        print("OPERATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nError during merge and deduplication: {e}")
        print("Please check the error and try again.")
        return

if __name__ == "__main__":
    main()







