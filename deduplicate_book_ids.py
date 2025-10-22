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

def generate_summary_report(results, output_file):
    """Generate a summary report of the deduplication process."""
    report = {
        'deduplication_summary': {
            'timestamp': datetime.now().isoformat(),
            'total_files_processed': results['total_files_processed'],
            'total_duplicates_removed': results['total_duplicates_removed'],
            'unique_books_total': results['unique_books_total'],
            'duplicates_per_file': results['duplicates_per_file']
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nSummary report saved to: {output_file}")
    return report

def main():
    """Main execution function."""
    book_ids_dir = "/Users/mohammed/Work/oreilly-books/book_ids"
    backup_dir = "/Users/mohammed/Work/oreilly-books/book_ids_backup"
    report_file = "/Users/mohammed/Work/oreilly-books/deduplication_report.json"
    
    print("=" * 60)
    print("BOOK ID DEDUPLICATION TOOL")
    print("=" * 60)
    
    # Verify directory exists
    if not os.path.exists(book_ids_dir):
        print(f"Error: Directory {book_ids_dir} does not exist")
        return
    
    # Create backup
    backup_count = create_backup(book_ids_dir, backup_dir)
    if backup_count == 0:
        print("No files to backup. Exiting.")
        return
    
    # Perform deduplication
    results = deduplicate_books(book_ids_dir)
    
    # Generate summary report
    summary = generate_summary_report(results, report_file)
    
    # Print final summary
    print("\n" + "=" * 60)
    print("DEDUPLICATION COMPLETE")
    print("=" * 60)
    print(f"Files processed: {results['total_files_processed']}")
    print(f"Total duplicates removed: {results['total_duplicates_removed']}")
    print(f"Unique books remaining: {results['unique_books_total']}")
    print(f"Backup created in: {backup_dir}")
    print(f"Summary report: {report_file}")
    
    # Show files with most duplicates removed
    if results['duplicates_per_file']:
        print("\nTop 10 files with most duplicates removed:")
        sorted_duplicates = sorted(
            results['duplicates_per_file'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        for filename, count in sorted_duplicates:
            if count > 0:
                print(f"  {filename}: {count} duplicates removed")

if __name__ == "__main__":
    main()

