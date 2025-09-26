#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Book Downloader for O'Reilly Learning
Downloads books as EPUB files using book IDs

Usage:
    python download_books.py <book_id> [options]
    python download_books.py --from-file <book_ids_file> [options]
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add the parser directory to Python path
parser_dir = Path(__file__).parent
sys.path.insert(0, str(parser_dir))

# Import our organized modules
from auth import AuthManager
from display import Display
from download import BookDownloader
from epub import EpubGenerator
from epub_enhanced import EnhancedEpubGenerator
from config import SAFARI_BASE_URL, HEADERS


class BookDownloadManager:
    """Manages book downloading and EPUB generation"""
    
    def __init__(self, use_auth=True, output_dir="outputs/downloaded_books"):
        self.use_auth = use_auth
        self.output_dir = output_dir
        self.session = None
        self.display = Display("book_downloader.log", os.path.dirname(os.path.realpath(__file__)))
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize authentication if requested
        if self.use_auth:
            self.auth_manager = AuthManager(self.display)
            # Initialize session and authenticate
            self.auth_manager.initialize_session()
            self.session = self.auth_manager.session
        else:
            import requests
            self.session = requests.Session()
            self.session.headers.update(HEADERS)
    
    def download_book(self, book_id: str, epub_mode: str = 'enhanced') -> bool:
        """
        Download a single book by ID
        
        Args:
            book_id: The book ID to download
            epub_mode: EPUB generation mode ('basic', 'enhanced', 'kindle', 'dual')
            
        Returns:
            bool: True if successful, False otherwise
        """
        self.display.info(f"📚 Downloading book: {book_id}")
        
        try:
            # Initialize book downloader
            downloader = BookDownloader(self.session, self.display, book_id)
            
            # Get book information
            self.display.info("📖 Retrieving book information...")
            book_info = downloader.get_book_info()
            
            if not book_info:
                self.display.error(f"❌ Failed to retrieve book info for {book_id}")
                return False
            
            book_title = book_info.get('title', 'Unknown Title')
            self.display.info(f"📖 Book: {book_title}")
            
            # Get book chapters
            self.display.info("📑 Retrieving book chapters...")
            chapters = downloader.get_book_chapters()
            
            if not chapters:
                self.display.error(f"❌ Failed to retrieve chapters for {book_id}")
                return False
            
            self.display.info(f"📑 Found {len(chapters)} chapters")
            
            # Set up book paths
            book_title = book_info.get('title', 'Unknown Title')
            clean_book_title = "".join(c for c in book_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            book_path = os.path.join(self.output_dir, f"{clean_book_title} ({book_id})")
            css_path = os.path.join(book_path, "OEBPS", "Styles")
            images_path = os.path.join(book_path, "OEBPS", "Images")
            
            # Create directories
            os.makedirs(book_path, exist_ok=True)
            os.makedirs(css_path, exist_ok=True)
            os.makedirs(images_path, exist_ok=True)
            
            # Create EPUB based on mode
            api_url = f"{SAFARI_BASE_URL}/api/v1/book/{book_id}/"
            generated_files = []
            
            if epub_mode == 'dual':
                # Generate both standard and Kindle versions
                self.display.info("📚 Generating dual EPUB files (Standard + Kindle)...")
                
                # Standard EPUB
                self.display.info("📚 Generating standard EPUB 3.3...")
                standard_generator = EnhancedEpubGenerator(
                    self.session, self.display, book_info, chapters,
                    book_path, css_path, images_path
                )
                standard_epub = standard_generator.create_enhanced_epub(api_url, book_id, self.output_dir, is_kindle=False)
                if standard_epub:
                    generated_files.append(standard_epub)
                
                # Kindle EPUB
                self.display.info("📚 Generating Kindle-optimized EPUB...")
                kindle_generator = EnhancedEpubGenerator(
                    self.session, self.display, book_info, chapters,
                    book_path, css_path, images_path
                )
                kindle_epub = kindle_generator.create_enhanced_epub(api_url, book_id, self.output_dir, is_kindle=True)
                if kindle_epub:
                    generated_files.append(kindle_epub)
                    
            elif epub_mode == 'kindle':
                # Generate Kindle-optimized EPUB
                self.display.info("📚 Generating Kindle-optimized EPUB...")
                kindle_generator = EnhancedEpubGenerator(
                    self.session, self.display, book_info, chapters,
                    book_path, css_path, images_path
                )
                kindle_epub = kindle_generator.create_enhanced_epub(api_url, book_id, self.output_dir, is_kindle=True)
                if kindle_epub:
                    generated_files.append(kindle_epub)
                    
            elif epub_mode == 'enhanced':
                # Generate enhanced EPUB
                self.display.info("📚 Generating enhanced EPUB 3.3...")
                enhanced_generator = EnhancedEpubGenerator(
                    self.session, self.display, book_info, chapters,
                    book_path, css_path, images_path
                )
                enhanced_epub = enhanced_generator.create_enhanced_epub(api_url, book_id, self.output_dir, is_kindle=False)
                if enhanced_epub:
                    generated_files.append(enhanced_epub)
                    
            else:  # basic
                # Generate basic EPUB
                self.display.info("📚 Generating basic EPUB...")
                basic_generator = EpubGenerator(
                    self.session, self.display, book_info, chapters,
                    book_path, css_path, images_path
                )
                basic_epub = basic_generator.create_epub(api_url, book_id, self.output_dir)
                if basic_epub:
                    generated_files.append(basic_epub)
            
            if generated_files:
                for epub_path in generated_files:
                    self.display.info(f"✅ EPUB created: {epub_path}")
                return True
            else:
                self.display.error(f"❌ Failed to create EPUB for {book_id}")
                return False
                
        except Exception as e:
            self.display.error(f"❌ Error downloading book {book_id}: {e}")
            return False
    
    def download_books_from_file(self, book_ids_file: str, epub_mode: str = 'enhanced') -> dict:
        """
        Download multiple books from a JSON file containing book IDs
        
        Args:
            book_ids_file: Path to JSON file with book IDs
            epub_mode: EPUB generation mode ('basic', 'enhanced', 'kindle', 'dual')
            
        Returns:
            dict: Results summary
        """
        self.display.info(f"📚 Loading book IDs from: {book_ids_file}")
        
        try:
            with open(book_ids_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract book IDs
            if isinstance(data, dict) and 'book_ids' in data:
                book_ids = data['book_ids']
            elif isinstance(data, list):
                book_ids = data
            else:
                self.display.error("❌ Invalid book IDs file format")
                return {'success': 0, 'failed': 0, 'total': 0}
            
            self.display.info(f"📚 Found {len(book_ids)} book IDs")
            
            # Download each book
            results = {'success': 0, 'failed': 0, 'total': len(book_ids)}
            
            for i, book_id in enumerate(book_ids, 1):
                self.display.info(f"📚 Processing book {i}/{len(book_ids)}: {book_id}")
                
                if self.download_book(book_id, epub_mode):
                    results['success'] += 1
                else:
                    results['failed'] += 1
            
            return results
            
        except Exception as e:
            self.display.error(f"❌ Error loading book IDs file: {e}")
            return {'success': 0, 'failed': 0, 'total': 0}


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(
        description='Download O\'Reilly Learning books as EPUB files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_books.py 9781098118723
  python download_books.py --from-file outputs/topic_results/generative-ai_book_ids_20250926_004629.json
  python download_books.py 9781098118723 --no-auth --output-dir my_books
        """
    )
    
    parser.add_argument('book_id', nargs='?', help='Book ID to download')
    parser.add_argument('--from-file', help='JSON file containing book IDs')
    parser.add_argument('--output-dir', default='outputs/downloaded_books', help='Output directory')
    parser.add_argument('--no-auth', action='store_true', help='Skip authentication')
    parser.add_argument('--basic-epub', action='store_true', help='Use basic EPUB generator instead of enhanced')
    parser.add_argument('--enhanced-epub', action='store_true', default=True, help='Use enhanced EPUB generator (default)')
    
    args = parser.parse_args()
    
    if not args.book_id and not args.from_file:
        parser.print_help()
        return
    
    # Initialize download manager
    download_manager = BookDownloadManager(
        use_auth=not args.no_auth,
        output_dir=args.output_dir
    )
    
    print("🚀 Starting book downloader")
    print("=" * 60)
    
    if args.from_file:
        # Download from file
        if not os.path.exists(args.from_file):
            print(f"❌ File not found: {args.from_file}")
            return
        
        print(f"📚 Downloading books from: {args.from_file}")
        results = download_manager.download_books_from_file(
            args.from_file, 
            enhanced_epub=not args.basic_epub
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
            enhanced_epub=not args.basic_epub
        )
        
        if success:
            print(f"✅ Successfully downloaded book {args.book_id}")
        else:
            print(f"❌ Failed to download book {args.book_id}")
    
    print(f"\n✅ Complete! Check the '{args.output_dir}' directory for downloaded books.")


if __name__ == "__main__":
    main()
