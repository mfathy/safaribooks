#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Book Downloader Script
Downloads O'Reilly Learning books as EPUB files

Usage:
    python main_downloader.py <book_id> [options]
    python main_downloader.py --from-file <book_ids_file> [options]
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add the book_downloader directory to Python path
downloader_dir = Path(__file__).parent / "book_downloader"
sys.path.insert(0, str(downloader_dir))

# Import downloader modules
from download_books import BookDownloadManager


def main():
    """Main function for the book downloader"""
    parser = argparse.ArgumentParser(
        description='Download O\'Reilly Learning books as EPUB files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_downloader.py 9781098118723
  python main_downloader.py --from-file book_lists/generative-ai_book_ids.json
  python main_downloader.py 9781098118723 --no-auth --output-dir my_books
        """
    )
    
    parser.add_argument('book_id', nargs='?', help='Book ID to download')
    parser.add_argument('--from-file', help='JSON file containing book IDs')
    parser.add_argument('--output-dir', default='books', help='Output directory for downloaded books')
    parser.add_argument('--no-auth', action='store_true', help='Skip authentication')
    parser.add_argument('--basic-epub', action='store_true', help='Use basic EPUB generator instead of enhanced')
    parser.add_argument('--enhanced', action='store_true', help='Generate enhanced EPUB 3.3 with improved metadata and formatting')
    parser.add_argument('--kindle', action='store_true', help='Generate Kindle-optimized EPUB with enhanced formatting')
    parser.add_argument('--dual', action='store_true', help='Generate both standard and Kindle-optimized EPUB files')
    
    args = parser.parse_args()
    
    if not args.book_id and not args.from_file:
        parser.print_help()
        return
    
    # Initialize download manager
    download_manager = BookDownloadManager(
        use_auth=not args.no_auth,
        output_dir=args.output_dir
    )
    
    print("🚀 Starting O'Reilly Book Downloader")
    print("=" * 60)
    
    # Determine EPUB generation mode
    if args.dual:
        epub_mode = 'dual'
    elif args.kindle:
        epub_mode = 'kindle'
    elif args.enhanced:
        epub_mode = 'enhanced'
    elif args.basic_epub:
        epub_mode = 'basic'
    else:
        epub_mode = 'enhanced'  # Default to enhanced
    
    if args.from_file:
        # Download from file
        if not os.path.exists(args.from_file):
            print(f"❌ File not found: {args.from_file}")
            return
        
        print(f"📚 Downloading books from: {args.from_file}")
        results = download_manager.download_books_from_file(
            args.from_file, 
            epub_mode=epub_mode
        )
        
        print(f"\n📊 Download Results:")
        print(f"   Total books: {results['total']}")
        print(f"   Successful: {results['success']}")
        print(f"   Failed: {results['failed']}")
        
        if results['failed'] > 0:
            print(f"   Success rate: {(results['success']/results['total']*100):.1f}%")
    
    else:
        # Download single book
        print(f"📚 Downloading book: {args.book_id}")
        
        success = download_manager.download_book(
            args.book_id, 
            epub_mode=epub_mode
        )
        
        if success:
            print(f"✅ Successfully downloaded book {args.book_id}")
        else:
            print(f"❌ Failed to download book {args.book_id}")
    
    print(f"\n✅ Complete! Check the '{args.output_dir}' directory for downloaded books.")


if __name__ == "__main__":
    main()
