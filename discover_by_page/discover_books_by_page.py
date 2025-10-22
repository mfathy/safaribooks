#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Books by Page Discovery Script
Discovers all O'Reilly books by paginating through the v1 search API
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Set, Optional
import logging
from datetime import datetime
import requests

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oreilly_parser.oreilly_books_parser import load_cookies


class BooksByPageDiscoverer:
    """Discovers all books by paginating through O'Reilly v1 search API"""
    
    def __init__(self, config_file: str = None, update_mode: bool = False):
        self.config = self._load_config(config_file)
        self.setup_logging()
        self.update_mode = update_mode
        
        # Load authentication cookies
        self.cookies = load_cookies()
        if not self.cookies:
            self.logger.warning("No authentication cookies found. Some content may not be accessible.")
        
        # Create output directories
        self.base_dir = Path(__file__).parent
        self.book_ids_dir = self.base_dir / 'book_ids'
        self.output_dir = self.base_dir / 'output'
        self.book_ids_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Progress tracking
        self.discovered_book_ids: Set[str] = set()
        self.duplicates_skipped: int = 0
        self.total_books_discovered: int = 0
        self.topics_created: Set[str] = set()
        self.progress_lock = None  # Will be set if threading is added later
        
        # Load existing progress if resuming
        if self.config.get('resume', True):
            self._load_progress()
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'max_pages': 4093,
            'discovery_delay': 1.5,
            'resume': True,
            'progress_file': 'output/discovery_by_page_progress.json',
            'verbose': False,
            'retry_failed': True,
            'max_retries': 3,
            'retry_delay': 5,
            'save_interval': 10,  # Save progress every N pages
            'log_file': 'book_discovery_by_page.log'
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config file {config_file}: {e}")
        
        return default_config
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.INFO
        if self.config.get('verbose', False):
            log_level = logging.DEBUG
        
        # Create log file path
        log_file = self.config['log_file']
        if not os.path.isabs(log_file):
            log_file = os.path.join(os.path.dirname(__file__), log_file)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('BooksByPageDiscoverer')
    
    def _load_progress(self):
        """Load previous discovery progress"""
        progress_file = self.config['progress_file']
        if not os.path.isabs(progress_file):
            progress_file = os.path.join(os.path.dirname(__file__), progress_file)
        
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    progress = json.load(f)
                self.discovered_book_ids = set(progress.get('discovered_book_ids', []))
                self.duplicates_skipped = progress.get('duplicates_skipped', 0)
                self.total_books_discovered = progress.get('total_books_discovered', 0)
                self.topics_created = set(progress.get('topics_created', []))
                self.logger.info(f"Loaded progress: {len(self.discovered_book_ids)} unique books, {self.duplicates_skipped} duplicates skipped")
            except Exception as e:
                self.logger.warning(f"Could not load progress file: {e}")
    
    def _save_progress(self, last_completed_page: int):
        """Save current discovery progress"""
        progress_file = self.config['progress_file']
        if not os.path.isabs(progress_file):
            progress_file = os.path.join(os.path.dirname(__file__), progress_file)
        
        try:
            progress = {
                'last_completed_page': last_completed_page,
                'discovered_book_ids': list(self.discovered_book_ids),
                'duplicates_skipped': self.duplicates_skipped,
                'total_books_discovered': self.total_books_discovered,
                'topics_created': list(self.topics_created),
                'timestamp': time.time()
            }
            with open(progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save progress: {e}")
    
    def _search_oreilly_api(self, page: int) -> Dict:
        """Search O'Reilly v1 API for all content on a specific page
        
        Args:
            page: Page number for pagination
        
        Returns:
            Dict containing search results with books list
        """
        url = "https://learning.oreilly.com/api/v1/search"
        params = {
            'q': '*',  # Wildcard to get all content
            'page': page
        }
        
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        }
        
        for attempt in range(self.config['max_retries']):
            try:
                response = requests.get(url, params=params, headers=headers, cookies=self.cookies, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt < self.config['max_retries'] - 1:
                    wait_time = self.config['retry_delay'] * (2 ** attempt)
                    self.logger.warning(f"API request failed for page {page} (attempt {attempt + 1}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"API request failed for page {page} after {self.config['max_retries']} attempts: {e}")
                    raise
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response for page {page}: {e}")
                raise
    
    def _sanitize_topic_name(self, topic_name: str) -> str:
        """Sanitize topic name for use as filename - lowercase with underscores"""
        sanitized = topic_name.strip().lower().replace(' ', '_')
        # Replace any problematic characters with underscores
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '&', '-', '(', ')', '.', ',', '+', '=']:
            sanitized = sanitized.replace(char, '_')
        # Replace multiple consecutive underscores with single underscore
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized
    
    def _validate_book(self, book: Dict) -> bool:
        """Validate if a book should be included based on validation rules
        
        Args:
            book: Book data from API response
            
        Returns:
            True if book should be included, False otherwise
        """
        # 1. Content type validation - Only books
        content_type = book.get('content_type', '').lower()
        if content_type not in ['book', 'ebook', '']:
            return False
        
        # 2. Format validation - Only books, skip videos, courses, audiobooks
        format_type = book.get('format', '').lower()
        if format_type not in ['book', 'ebook', '']:
            return False
        
        # 3. Book ID validation - Must have valid book ID
        book_id = book.get('archive_id') or book.get('isbn') or book.get('ourn')
        if not book_id:
            return False
        
        # 4. Title validation - Must have meaningful title
        title = book.get('title', '').strip()
        if len(title) < 4:  # Updated to 4 characters as requested
            return False
        
        # 5. Language validation - English only (if specified)
        language = book.get('language', '').lower()
        if language and language not in ['en', 'english', '']:
            return False
        
        # 6. Topics/Subjects validation - Must have at least one topic
        topics = book.get('topics', [])
        subjects = book.get('subjects', [])
        if not topics and not subjects:
            return False
        
        return True
    
    def _extract_book_info(self, book: Dict) -> Dict:
        """Extract book information in the required format
        
        Args:
            book: Book data from API response
            
        Returns:
            Dict with extracted book information
        """
        book_id = book.get('archive_id') or book.get('isbn') or book.get('ourn')
        isbn = book.get('isbn', '').strip()
        
        # Get topics (prefer topics over subjects)
        topics = book.get('topics', [])
        subjects = book.get('subjects', [])
        
        # Extract topic names
        topic_names = []
        if topics:
            topic_names = [t.get('name', '') for t in topics if t.get('name')]
        elif subjects:
            topic_names = [s.get('name', '') if isinstance(s, dict) else str(s) for s in subjects]
        
        # Filter out empty topic names
        topic_names = [t for t in topic_names if t.strip()]
        
        book_info = {
            'title': book.get('title', ''),
            'id': f"https://www.safaribooksonline.com/api/v1/book/{book_id}/",
            'url': book.get('url', f"https://learning.oreilly.com/api/v1/book/{book_id}/"),
            'isbn': isbn if isbn else book_id,
            'format': book.get('format', 'book'),
            'main_topic': topic_names[0] if topic_names else 'Unknown',
            'secondary_topics': topic_names[1:] if len(topic_names) > 1 else []
        }
        
        return book_info
    
    def _load_topic_file(self, topic_name: str) -> Dict:
        """Load existing topic file or create new structure
        
        Args:
            topic_name: Name of the topic
            
        Returns:
            Dict with topic file data
        """
        sanitized_name = self._sanitize_topic_name(topic_name)
        topic_file = self.book_ids_dir / f"{sanitized_name}_books.json"
        
        if topic_file.exists():
            try:
                with open(topic_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load topic file {topic_file}: {e}")
        
        # Create new topic structure
        return {
            'skill_name': topic_name,
            'discovery_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_books': 0,
            'books': []
        }
    
    def _save_topic_file(self, topic_name: str, topic_data: Dict):
        """Save topic file with updated data
        
        Args:
            topic_name: Name of the topic
            topic_data: Topic data to save
        """
        sanitized_name = self._sanitize_topic_name(topic_name)
        topic_file = self.book_ids_dir / f"{sanitized_name}_books.json"
        
        try:
            # Update timestamp
            topic_data['discovery_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(topic_file, 'w', encoding='utf-8') as f:
                json.dump(topic_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Saved topic file: {topic_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save topic file {topic_file}: {e}")
    
    def _add_book_to_topic(self, book_info: Dict, topic_name: str):
        """Add a book to a topic file, checking for duplicates
        
        Args:
            book_info: Book information
            topic_name: Name of the topic
        """
        # Check if book already exists globally
        book_id = book_info['isbn']
        if book_id in self.discovered_book_ids:
            self.duplicates_skipped += 1
            self.logger.debug(f"Duplicate book skipped: {book_info['title']}")
            return
        
        # Load topic file
        topic_data = self._load_topic_file(topic_name)
        
        # Check if book already exists in this topic file
        existing_book_ids = {book['isbn'] for book in topic_data['books']}
        if book_id in existing_book_ids:
            self.logger.debug(f"Book already exists in topic {topic_name}: {book_info['title']}")
            return
        
        # Add book to topic
        topic_data['books'].append(book_info)
        topic_data['total_books'] = len(topic_data['books'])
        
        # Save topic file
        self._save_topic_file(topic_name, topic_data)
        
        # Update global tracking
        self.discovered_book_ids.add(book_id)
        self.total_books_discovered += 1
        self.topics_created.add(topic_name)
        
        self.logger.debug(f"Added book to {topic_name}: {book_info['title']}")
    
    def discover_books_by_page(self, start_page: int = 1, end_page: int = None) -> Dict:
        """Discover all books by paginating through the API
        
        Args:
            start_page: Page to start from (default: 1)
            end_page: Page to end at (default: max_pages from config)
            
        Returns:
            Dict with discovery results
        """
        if end_page is None:
            end_page = self.config['max_pages']
        
        self.logger.info(f"Starting book discovery from page {start_page} to {end_page}")
        self.logger.info(f"Total pages to process: {end_page - start_page + 1}")
        
        start_time = time.time()
        pages_processed = 0
        books_found_this_session = 0
        
        try:
            for page in range(start_page, end_page + 1):
                self.logger.debug(f"Processing page {page}")
                
                # Make API request
                response_data = self._search_oreilly_api(page)
                results = response_data.get('results', [])
                
                if not results:
                    self.logger.warning(f"No results found on page {page}, stopping")
                    break
                
                books_added_this_page = 0
                
                # Process each result
                for item in results:
                    if self._validate_book(item):
                        book_info = self._extract_book_info(item)
                        
                        # Add to main topic
                        main_topic = book_info['main_topic']
                        if main_topic and main_topic != 'Unknown':
                            self._add_book_to_topic(book_info, main_topic)
                            books_added_this_page += 1
                        
                        # Add to secondary topics
                        for secondary_topic in book_info['secondary_topics']:
                            if secondary_topic:
                                self._add_book_to_topic(book_info, secondary_topic)
                
                pages_processed += 1
                books_found_this_session += books_added_this_page
                
                # Progress logging
                if page % 10 == 0 or page == start_page:
                    elapsed = time.time() - start_time
                    progress_pct = ((page - start_page + 1) / (end_page - start_page + 1)) * 100
                    eta_seconds = (elapsed / (page - start_page + 1)) * (end_page - page)
                    eta_hours = eta_seconds / 3600
                    
                    self.logger.info(f"[Page {page}/{end_page}] ({progress_pct:.1f}%) | "
                                   f"Books: {self.total_books_discovered:,} | "
                                   f"Topics: {len(self.topics_created)} | "
                                   f"Duplicates: {self.duplicates_skipped} | "
                                   f"ETA: ~{eta_hours:.1f}h")
                
                # Save progress periodically
                if page % self.config['save_interval'] == 0:
                    self._save_progress(page)
                
                # Add delay between requests
                time.sleep(self.config['discovery_delay'])
        
        except KeyboardInterrupt:
            self.logger.info("Discovery interrupted by user")
            self._save_progress(page)
            raise
        except Exception as e:
            self.logger.error(f"Error during discovery: {e}")
            self._save_progress(page)
            raise
        
        # Final progress save
        self._save_progress(end_page)
        
        # Calculate final statistics
        elapsed_time = time.time() - start_time
        
        result = {
            'pages_processed': pages_processed,
            'total_books_discovered': self.total_books_discovered,
            'books_found_this_session': books_found_this_session,
            'duplicates_skipped': self.duplicates_skipped,
            'topics_created': len(self.topics_created),
            'execution_time_hours': elapsed_time / 3600,
            'success': True
        }
        
        return result
    
    def create_summary_file(self, results: Dict):
        """Create a human-readable summary file"""
        summary_file = self.base_dir / 'discovery_summary_by_page.txt'
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("O'REILLY BOOKS DISCOVERY BY PAGE SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Pages Processed: {results['pages_processed']}\n")
            f.write(f"Total Books Discovered: {results['total_books_discovered']:,}\n")
            f.write(f"Books Found This Session: {results['books_found_this_session']:,}\n")
            f.write(f"Duplicates Skipped: {results['duplicates_skipped']:,}\n")
            f.write(f"Topics Created: {results['topics_created']}\n")
            f.write(f"Execution Time: {results['execution_time_hours']:.2f} hours\n\n")
            
            f.write("TOPICS BY BOOK COUNT:\n")
            f.write("-" * 30 + "\n")
            
            # Get topic file sizes
            topic_sizes = []
            for topic_file in self.book_ids_dir.glob("*_books.json"):
                try:
                    with open(topic_file, 'r') as f:
                        data = json.load(f)
                        topic_sizes.append((data['skill_name'], data['total_books']))
                except:
                    continue
            
            topic_sizes.sort(key=lambda x: x[1], reverse=True)
            
            for topic_name, count in topic_sizes[:20]:  # Top 20
                f.write(f"{topic_name}: {count:,} books\n")
            
            if len(topic_sizes) > 20:
                f.write(f"... and {len(topic_sizes) - 20} more topics\n")
            
            f.write(f"\nTopic files saved in: {self.book_ids_dir}/\n")
            f.write(f"Progress file: {self.config['progress_file']}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Discover All O'Reilly Books by Page",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full discovery from scratch
  python3 discover_books_by_page.py
  
  # Resume from last saved progress
  python3 discover_books_by_page.py --resume
  
  # Update existing library (re-process all pages)
  python3 discover_books_by_page.py --update
  
  # Verbose logging
  python3 discover_books_by_page.py --verbose
  
  # Custom delay between requests
  python3 discover_books_by_page.py --delay 2
  
  # Start from specific page
  python3 discover_books_by_page.py --start-page 100
  
  # Process only specific page range
  python3 discover_books_by_page.py --start-page 100 --end-page 200
        """
    )
    
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--start-page', type=int, default=1, help='Page to start from (default: 1)')
    parser.add_argument('--end-page', type=int, help='Page to end at (default: 4093)')
    parser.add_argument('--delay', type=float, help='Delay between requests in seconds')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--update', '-u', action='store_true', help='Re-process all pages (update existing files)')
    parser.add_argument('--resume', '-r', action='store_true', help='Resume from last saved progress')
    
    args = parser.parse_args()
    
    # Initialize discoverer
    discoverer = BooksByPageDiscoverer(args.config, update_mode=args.update)
    
    # Override config with command line arguments
    if args.delay:
        discoverer.config['discovery_delay'] = args.delay
    if args.verbose:
        discoverer.config['verbose'] = True
        discoverer.setup_logging()  # Re-setup logging with new level
    
    # Determine start page
    start_page = args.start_page
    if args.resume and not args.update:
        # Load progress to get last completed page
        progress_file = discoverer.config['progress_file']
        if not os.path.isabs(progress_file):
            progress_file = os.path.join(os.path.dirname(__file__), progress_file)
        
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    progress = json.load(f)
                start_page = progress.get('last_completed_page', 1) + 1
                discoverer.logger.info(f"Resuming from page {start_page}")
            except:
                discoverer.logger.warning("Could not load progress file, starting from page 1")
    
    try:
        # Start the discovery process
        results = discoverer.discover_books_by_page(start_page, args.end_page)
        
        # Create summary
        discoverer.create_summary_file(results)
        
        # Print final summary
        print(f"\n🎉 Discovery completed!")
        print(f"📚 Discovered {results['total_books_discovered']:,} total books")
        print(f"📖 Found {results['books_found_this_session']:,} new books this session")
        print(f"📁 Organized in {results['topics_created']} topic files")
        print(f"⏭️  Skipped {results['duplicates_skipped']:,} duplicates")
        print(f"📊 Check 'discovery_summary_by_page.txt' for detailed breakdown")
        
    except KeyboardInterrupt:
        print("\n⚠️  Discovery interrupted by user")
        print("💾 Progress saved - you can resume later with --resume")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

