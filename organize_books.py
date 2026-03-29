#!/usr/bin/env python3
"""
Organize downloaded books from books_by_skills folder.

This script:
1. Reads book IDs from oreilly-books-2026-01-25.json
2. Scans all downloaded books in books_by_skills directories
3. Moves books that are in the JSON to "All Books" folder
4. Removes books that are NOT in the JSON
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Set, Dict, List, Tuple
from datetime import datetime


class BookOrganizer:
    def __init__(self, json_file: str, books_by_skills_dir: str, all_books_dir: str = "All Books"):
        self.json_file = Path(json_file)
        self.books_by_skills_dir = Path(books_by_skills_dir)
        self.all_books_dir = self.books_by_skills_dir / all_books_dir
        self.book_ids: Set[str] = set()
        self.stats = {
            "total_in_json": 0,
            "books_found": 0,
            "books_moved": 0,
            "books_removed": 0,
            "errors": 0
        }
        self.log_lines: List[str] = []
        
    def log(self, message: str, level: str = "INFO"):
        """Add a log message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        self.log_lines.append(log_msg)
        print(log_msg)
    
    def load_book_ids(self) -> Set[str]:
        """Load all book IDs from the JSON file."""
        self.log("Loading book IDs from JSON file...")
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            book_ids = set()
            for book in data:
                if 'bookId' in book:
                    book_ids.add(book['bookId'])
            
            self.stats["total_in_json"] = len(book_ids)
            self.book_ids = book_ids
            self.log(f"✓ Loaded {len(book_ids)} book IDs from JSON")
            return book_ids
        except Exception as e:
            self.log(f"✗ Error loading JSON file: {e}", "ERROR")
            self.stats["errors"] += 1
            raise
    
    def extract_book_id_from_folder(self, folder_name: str) -> str:
        """Extract book ID from folder name like 'Book Title (9781234567890)'."""
        # Pattern: (digits) at the end of the folder name
        match = re.search(r'\((\d+)\)$', folder_name)
        if match:
            return match.group(1)
        return None
    
    def find_all_book_folders(self) -> List[Tuple[Path, str, str]]:
        """Find all book folders in books_by_skills directory."""
        self.log("Scanning books_by_skills directory for downloaded books...")
        book_folders = []
        
        if not self.books_by_skills_dir.exists():
            self.log(f"✗ Directory not found: {self.books_by_skills_dir}", "ERROR")
            return book_folders
        
        # Walk through all skill directories
        for skill_dir in self.books_by_skills_dir.iterdir():
            # Skip non-directories
            if not skill_dir.is_dir():
                continue
            
            # Process "All Books" directory separately (only check for removal, not move)
            if skill_dir.name == "All Books":
                # Look for book folders in "All Books" that might need removal
                for item in skill_dir.iterdir():
                    if item.is_dir():
                        book_id = self.extract_book_id_from_folder(item.name)
                        if book_id:
                            # Mark as already in "All Books" by using a special marker
                            book_folders.append((item, book_id, "all_books"))
                            self.stats["books_found"] += 1
                continue
            
            # Process skill directories (move books to "All Books")
            for item in skill_dir.iterdir():
                if item.is_dir():
                    book_id = self.extract_book_id_from_folder(item.name)
                    if book_id:
                        book_folders.append((item, book_id, "skill_dir"))
                        self.stats["books_found"] += 1
        
        self.log(f"✓ Found {len(book_folders)} downloaded book folders")
        return book_folders
    
    def move_book_to_all_books(self, book_path: Path, book_id: str) -> bool:
        """Move a book folder to 'All Books' directory."""
        try:
            destination = self.all_books_dir / book_path.name
            
            # Create "All Books" directory if it doesn't exist
            self.all_books_dir.mkdir(parents=True, exist_ok=True)
            
            # If destination already exists, handle it
            if destination.exists():
                # Check if it's the same book (same ID)
                existing_id = self.extract_book_id_from_folder(destination.name)
                if existing_id == book_id:
                    self.log(f"  ⚠ Book already exists in All Books: {book_path.name}")
                    # Remove the source since it's already in All Books
                    shutil.rmtree(book_path)
                    return True
                else:
                    # Different book with similar name, rename destination
                    counter = 1
                    while destination.exists():
                        base_name = book_path.stem if hasattr(book_path, 'stem') else book_path.name
                        new_name = f"{base_name}_copy{counter}"
                        destination = self.all_books_dir / new_name
                        counter += 1
            
            # Move the book folder
            shutil.move(str(book_path), str(destination))
            self.stats["books_moved"] += 1
            self.log(f"  ✓ Moved: {book_path.name} → All Books/")
            return True
            
        except Exception as e:
            self.log(f"  ✗ Error moving {book_path.name}: {e}", "ERROR")
            self.stats["errors"] += 1
            return False
    
    def remove_book(self, book_path: Path, book_id: str) -> bool:
        """Remove a book folder that is not in the JSON."""
        try:
            shutil.rmtree(book_path)
            self.stats["books_removed"] += 1
            self.log(f"  ✗ Removed: {book_path.name} (not in JSON)")
            return True
        except Exception as e:
            self.log(f"  ✗ Error removing {book_path.name}: {e}", "ERROR")
            self.stats["errors"] += 1
            return False
    
    def organize_books(self, dry_run: bool = False):
        """Main method to organize books."""
        self.log("=" * 80)
        self.log("BOOK ORGANIZATION SCRIPT")
        self.log("=" * 80)
        
        if dry_run:
            self.log("DRY RUN MODE - No files will be moved or deleted")
        
        # Load book IDs from JSON
        self.load_book_ids()
        
        # Find all book folders
        book_folders = self.find_all_book_folders()
        
        if not book_folders:
            self.log("No book folders found. Exiting.")
            return
        
        self.log("")
        self.log("-" * 80)
        self.log("PROCESSING BOOKS")
        self.log("-" * 80)
        
        # Process each book folder
        books_to_move = []
        books_to_remove = []
        
        for book_path, book_id, location in book_folders:
            if book_id in self.book_ids:
                # Only move if it's in a skill directory (not already in "All Books")
                if location == "skill_dir":
                    books_to_move.append((book_path, book_id))
                # If already in "All Books", keep it there (no action needed)
            else:
                # Remove books not in JSON, regardless of location
                books_to_remove.append((book_path, book_id))
        
        # Show summary before processing
        self.log("")
        self.log(f"Summary:")
        self.log(f"  • Books to move to 'All Books': {len(books_to_move)}")
        self.log(f"  • Books to remove: {len(books_to_remove)}")
        self.log("")
        
        if dry_run:
            self.log("DRY RUN - Would move:")
            for book_path, book_id in books_to_move:
                self.log(f"  → {book_path.name}")
            
            self.log("")
            self.log("DRY RUN - Would remove:")
            for book_path, book_id in books_to_remove:
                self.log(f"  → {book_path.name}")
            return
        
        # Move books to "All Books"
        if books_to_move:
            self.log("")
            self.log("Moving books to 'All Books' folder...")
            for book_path, book_id in books_to_move:
                self.move_book_to_all_books(book_path, book_id)
        
        # Remove books not in JSON
        if books_to_remove:
            self.log("")
            self.log("Removing books not in JSON...")
            for book_path, book_id in books_to_remove:
                self.remove_book(book_path, book_id)
        
        # Print final summary
        self.print_summary()
    
    def print_summary(self):
        """Print final summary statistics."""
        self.log("")
        self.log("=" * 80)
        self.log("SUMMARY")
        self.log("=" * 80)
        self.log(f"Total books in JSON:        {self.stats['total_in_json']}")
        self.log(f"Books found in folders:      {self.stats['books_found']}")
        self.log(f"Books moved to 'All Books':  {self.stats['books_moved']}")
        self.log(f"Books removed:               {self.stats['books_removed']}")
        self.log(f"Errors:                      {self.stats['errors']}")
        self.log("=" * 80)
    
    def save_log(self, log_file: str = "book_organization.log"):
        """Save log to file."""
        log_path = Path(log_file)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.log_lines))
        self.log(f"Log saved to: {log_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Organize downloaded books from books_by_skills folder"
    )
    parser.add_argument(
        '--json',
        default='oreilly-books-2026-01-25.json',
        help='Path to JSON file with book IDs (default: oreilly-books-2026-01-25.json)'
    )
    parser.add_argument(
        '--books-dir',
        default='books_by_skills',
        help='Path to books_by_skills directory (default: books_by_skills)'
    )
    parser.add_argument(
        '--all-books-dir',
        default='All Books',
        help='Name of the "All Books" directory (default: All Books)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually moving or deleting files'
    )
    parser.add_argument(
        '--log-file',
        default='book_organization.log',
        help='Path to save log file (default: book_organization.log)'
    )
    
    args = parser.parse_args()
    
    # Get absolute paths
    script_dir = Path(__file__).parent.absolute()
    json_path = script_dir / args.json if not Path(args.json).is_absolute() else Path(args.json)
    books_dir = script_dir / args.books_dir if not Path(args.books_dir).is_absolute() else Path(args.books_dir)
    
    organizer = BookOrganizer(
        json_file=str(json_path),
        books_by_skills_dir=str(books_dir),
        all_books_dir=args.all_books_dir
    )
    
    try:
        organizer.organize_books(dry_run=args.dry_run)
        organizer.save_log(args.log_file)
    except KeyboardInterrupt:
        organizer.log("\n✗ Interrupted by user", "ERROR")
        organizer.save_log(args.log_file)
    except Exception as e:
        organizer.log(f"\n✗ Fatal error: {e}", "ERROR")
        organizer.save_log(args.log_file)
        raise


if __name__ == "__main__":
    main()
