#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Topic Downloader Script
Parses a topic and downloads all books as EPUB files

Usage:
    python main_topic_downloader.py <topic-name> [options]
    python main_topic_downloader.py --from-file <book_ids_file> [options]
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add the book_parser and book_downloader directories to Python path
parser_dir = Path(__file__).parent / "book_parser"
downloader_dir = Path(__file__).parent / "book_downloader"
sys.path.insert(0, str(parser_dir))
sys.path.insert(0, str(downloader_dir))

# Import modules
from topic_book_parser import TopicBookParser
from download_books import BookDownloadManager


def main():
    """Main function for the topic downloader"""
    parser = argparse.ArgumentParser(
        description='Parse a topic and download all books as EPUB files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_topic_downloader.py generative-ai
  python main_topic_downloader.py python --max-pages 5 --delay 1.0
  python main_topic_downloader.py --from-file book_lists/generative-ai_book_ids.json
        """
    )
    
    parser.add_argument('topic_name', nargs='?', help='Topic slug to parse and download')
    parser.add_argument('--from-file', help='JSON file containing book IDs to download')
    parser.add_argument('--max-pages', type=int, help='Maximum number of pages to fetch (for topic parsing)')
    parser.add_argument('--page-size', type=int, default=100, help='Results per page (max 100)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests (seconds)')
    parser.add_argument('--no-auth', action='store_true', help='Skip authentication')
    parser.add_argument('--output-dir', default='books', help='Output directory for downloaded books')
    parser.add_argument('--basic-epub', action='store_true', help='Use basic EPUB generator instead of enhanced')
    parser.add_argument('--parse-only', action='store_true', help='Only parse topic, do not download books')
    
    args = parser.parse_args()
    
    if not args.topic_name and not args.from_file:
        parser.print_help()
        return
    
    print("🚀 Starting Topic Downloader")
    print("=" * 60)
    
    book_ids = []
    
    if args.from_file:
        # Load book IDs from file
        if not os.path.exists(args.from_file):
            print(f"❌ File not found: {args.from_file}")
            return
        
        print(f"📚 Loading book IDs from: {args.from_file}")
        try:
            with open(args.from_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract book IDs
            if isinstance(data, dict) and 'book_ids' in data:
                book_ids = data['book_ids']
            elif isinstance(data, list):
                book_ids = data
            else:
                print("❌ Invalid book IDs file format")
                return
            
            print(f"📚 Found {len(book_ids)} book IDs")
            
        except Exception as e:
            print(f"❌ Error loading book IDs file: {e}")
            return
    
    else:
        # Parse topic to get book IDs
        print(f"🔍 Parsing topic: {args.topic_name}")
        
        # Initialize topic parser
        topic_parser = TopicBookParser(
            use_auth=not args.no_auth,
            output_dir='book_lists'
        )
        
        # Fetch books for the topic
        results = topic_parser.get_books_for_topic(
            topic_slug=args.topic_name,
            max_pages=args.max_pages,
            page_size=args.page_size,
            delay=args.delay
        )
        
        # Display parsing results
        print(f"\n📊 Parsing Results:")
        print(f"   Books found: {results['total_books_found']}")
        print(f"   Unique book IDs: {results['unique_book_ids']}")
        print(f"   API total count: {results['total_count_from_api']}")
        print(f"   Pages fetched: {results['pages_fetched']}")
        print(f"   API errors: {results['api_errors']}")
        
        if results.get('page_limit_reached', False):
            print(f"   ⚠️  Page limit reached: Only first 10 pages available")
        
        # Save parsing results
        topic_parser.save_results(results, args.topic_name)
        
        # Extract book IDs
        book_ids = results['book_ids']
        
        if not book_ids:
            print("❌ No book IDs found to download")
            return
        
        print(f"📚 Extracted {len(book_ids)} book IDs for downloading")
    
    if args.parse_only:
        print("✅ Parse-only mode: Skipping download")
        return
    
    # Download books
    print(f"\n📚 Starting download of {len(book_ids)} books...")
    print("=" * 60)
    
    # Initialize download manager
    download_manager = BookDownloadManager(
        use_auth=not args.no_auth,
        output_dir=args.output_dir
    )
    
    # Download each book
    results = {'success': 0, 'failed': 0, 'total': len(book_ids)}
    
    for i, book_id in enumerate(book_ids, 1):
        print(f"📚 Processing book {i}/{len(book_ids)}: {book_id}")
        
        if download_manager.download_book(book_id, enhanced_epub=not args.basic_epub):
            results['success'] += 1
            print(f"   ✅ Success")
        else:
            results['failed'] += 1
            print(f"   ❌ Failed")
    
    # Display final results
    print(f"\n📊 Download Results:")
    print(f"   Total books: {results['total']}")
    print(f"   Successful: {results['success']}")
    print(f"   Failed: {results['failed']}")
    
    if results['failed'] > 0:
        print(f"   Success rate: {(results['success']/results['total']*100):.1f}%")
    
    print(f"\n✅ Complete! Check the '{args.output_dir}' directory for downloaded books.")


if __name__ == "__main__":
    main()
