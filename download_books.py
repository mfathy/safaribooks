#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Book Downloader Script - Step 2
Downloads actual books from previously discovered book IDs
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Set
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from oreilly_books import OreillyBooks
from progress_tracker import ProgressTracker, format_progress_line


class BookDownloader:
    """Downloads books from discovered book IDs"""
    
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        self.setup_logging()
        
        # Create base directory structure
        self.base_dir = Path(self.config.get('base_directory', 'books_by_skills'))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Book IDs directory
        self.book_ids_dir = Path(self.config.get('book_ids_directory', 'book_ids'))
        if not self.book_ids_dir.exists():
            raise FileNotFoundError(f"Book IDs directory not found: {self.book_ids_dir}")
        
        # Progress tracking with enhanced tracker
        self.progress_tracker = ProgressTracker(self.config['progress_file'], "download")
        self.downloaded_books: Set[str] = set(self.progress_tracker.data['completed_items'])
        self.failed_books: Dict[str, str] = dict(self.progress_tracker.data['failed_items'])
        self.progress_lock = Lock()
        
        # Initialize shared session for all downloads (prevents rate limiting)
        self._init_shared_session()
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'base_directory': 'books_by_skills',
            'book_ids_directory': 'book_ids',
            'max_books_per_skill': 1000,
            'download_delay': 5,
            'max_workers': 2,
            'epub_format': 'dual',
            'resume': True,
            'progress_file': 'download_progress.json',
            'verbose': False,
            'retry_failed': True,
            'max_retries': 3,
            'retry_delay': 10,
            'exclude_skills': [],
            'priority_skills': [
                "Python",
                "Machine Learning", 
                "AI & ML",
                "Data Science",
                "Deep Learning",
                "Artificial Intelligence (AI)"
            ]
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
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('book_downloader.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('BookDownloader')
    
    def _init_shared_session(self):
        """Initialize tracking for session creation (to prevent rate limiting)"""
        import time
        self.last_session_time = 0
        self.session_delay = 2  # Minimum 2 seconds between new sessions
        self.logger.info("Session rate limiting initialized")
    
    def _save_progress(self):
        """Save current download progress"""
        self.progress_tracker.save()
    
    def load_skill_books(self, skill_filter: List[str] = None) -> Dict[str, List[Dict]]:
        """Load discovered books for skills"""
        skill_books = {}
        
        # Find all skill JSON files
        skill_files = list(self.book_ids_dir.glob("*_books.json"))
        
        for skill_file in skill_files:
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                
                skill_name = skill_data.get('skill_name', skill_file.stem.replace('_books', ''))
                books = skill_data.get('books', [])
                
                # Apply filters
                if skill_filter and not any(f.lower() in skill_name.lower() for f in skill_filter):
                    continue
                
                if self.config.get('exclude_skills') and skill_name in self.config['exclude_skills']:
                    continue
                
                skill_books[skill_name] = books
                
            except Exception as e:
                self.logger.warning(f"Could not load skill file {skill_file}: {e}")
        
        self.logger.info(f"Loaded {len(skill_books)} skills with book data")
        return skill_books
    
    def _sanitize_skill_name(self, skill_name: str) -> str:
        """Sanitize skill name for use as directory name"""
        sanitized = skill_name.strip()
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            sanitized = sanitized.replace(char, '_')
        return sanitized
    
    def _get_skill_directory(self, skill_name: str) -> Path:
        """Get the directory path for a skill"""
        sanitized_name = self._sanitize_skill_name(skill_name)
        return self.base_dir / sanitized_name
    
    def download_single_book(self, book_info: Dict, skill_name: str, skill_dir: Path) -> bool:
        """Download a single book"""
        book_id_raw = book_info.get('id', '')
        
        # Extract numeric ID from URL if needed
        if isinstance(book_id_raw, str):
            if book_id_raw.startswith('http'):
                # Extract ISBN from URL like "https://www.safaribooksonline.com/api/v1/book/9781234567890/"
                import re
                match = re.search(r'/book/(\d+)/', book_id_raw)
                if match:
                    book_id = match.group(1)
                else:
                    # Try to get the last numeric segment
                    parts = [p for p in book_id_raw.split('/') if p and p.isdigit()]
                    book_id = parts[-1] if parts else book_id_raw
            else:
                book_id = book_id_raw
        else:
            book_id = str(book_id_raw)
        
        book_title = book_info.get('title', f'Book {book_id}')
        
        # Check if already downloaded (use raw ID for tracking to avoid duplicates)
        tracking_id = book_id_raw if book_id_raw else book_id
        with self.progress_lock:
            if tracking_id in self.downloaded_books or book_id in self.downloaded_books:
                self.logger.info(f"⏭️  Skipping {book_title} (already downloaded)")
                return True
        
        self.logger.info(f"📚 Downloading: {book_title} (ID: {book_id})")
        
        try:
            # Ensure skill directory exists
            skill_dir.mkdir(parents=True, exist_ok=True)
            
            # Create temporary args for the downloader
            class Args:
                def __init__(self, book_id, epub_format):
                    self.bookid = book_id
                    self.cred = None
                    self.no_cookies = False
                    self.kindle = epub_format in ['kindle', 'dual']
                    self.enhanced = epub_format in ['enhanced', 'dual']
                    self.dual = epub_format == 'dual'
                    self.log = False
            
            args = Args(book_id, self.config['epub_format'])
            
            # Add delay between session creations to prevent rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_session_time
            if time_since_last < self.session_delay:
                wait_time = self.session_delay - time_since_last
                self.logger.debug(f"Waiting {wait_time:.1f}s before creating new session...")
                time.sleep(wait_time)
            self.last_session_time = time.time()
            
            # Set output path to skill directory (instead of changing directory)
            # The downloader will create Books/ subdirectory, so we pass parent
            original_path_env = os.environ.get('OREILLY_OUTPUT_PATH')
            os.environ['OREILLY_OUTPUT_PATH'] = str(skill_dir.absolute())
            
            try:
                # Initialize and run the downloader
                downloader = OreillyBooks(args)
                
                # Mark as downloaded (use tracking ID for consistency)
                with self.progress_lock:
                    self.downloaded_books.add(tracking_id)
                    self.progress_tracker.add_completed_item(tracking_id)
                
                self.logger.info(f"✅ Successfully downloaded: {book_title}")
                return True
                
            finally:
                # Restore original environment
                if original_path_env:
                    os.environ['OREILLY_OUTPUT_PATH'] = original_path_env
                elif 'OREILLY_OUTPUT_PATH' in os.environ:
                    del os.environ['OREILLY_OUTPUT_PATH']
                
        except Exception as e:
            self.logger.error(f"❌ Failed to download {book_title}: {e}")
            with self.progress_lock:
                self.failed_books[tracking_id] = str(e)
                self.progress_tracker.add_failed_item(tracking_id, str(e))
            return False
    
    def download_books_for_skill(self, skill_name: str, books: List[Dict]) -> Dict[str, int]:
        """Download all books for a specific skill"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Downloading books for skill: {skill_name}")
        self.logger.info(f"{'='*60}")
        
        # Create skill directory
        skill_dir = self._get_skill_directory(skill_name)
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # Limit books if specified
        max_books = self.config.get('max_books_per_skill', 1000)
        if len(books) > max_books:
            self.logger.info(f"Limiting {skill_name} to {max_books} books (found {len(books)})")
            books = books[:max_books]
        
        self.logger.info(f"Downloading {len(books)} books for {skill_name}")
        
        # Update progress tracker
        self.progress_tracker.update_current_skill(skill_name, 0, len(books))
        
        # Download books
        results = {'total': len(books), 'downloaded': 0, 'failed': 0, 'skipped': 0}
        
        if self.config['max_workers'] > 1:
            # Parallel downloads
            with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
                future_to_book = {
                    executor.submit(self.download_single_book, book_info, skill_name, skill_dir): book_info
                    for book_info in books
                }
                
                for future in as_completed(future_to_book):
                    book_info = future_to_book[future]
                    try:
                        success = future.result()
                        if success:
                            results['downloaded'] += 1
                        else:
                            results['failed'] += 1
                    except Exception as e:
                        self.logger.error(f"Exception downloading {book_info.get('title', 'Unknown')}: {e}")
                        results['failed'] += 1
                    
                    # Save progress periodically
                    self._save_progress()
                    
                    # Add delay between downloads
                    time.sleep(self.config['download_delay'])
        else:
            # Sequential downloads
            for book_info in books:
                success = self.download_single_book(book_info, skill_name, skill_dir)
                if success:
                    results['downloaded'] += 1
                else:
                    results['failed'] += 1
                
                # Save progress
                self._save_progress()
                
                # Add delay between downloads
                time.sleep(self.config['download_delay'])
        
        # Count skipped books
        results['skipped'] = len([b for b in books if b.get('id', '') in self.downloaded_books]) - results['downloaded']
        
        # Mark skill as completed
        self.progress_tracker.complete_skill(skill_name)
        
        self.logger.info(f"Completed {skill_name}: {results}")
        return results
    
    def download_all_books(self, skill_filter: List[str] = None) -> Dict[str, Dict]:
        """Download books for all skills"""
        skill_books = self.load_skill_books(skill_filter)
        
        if not skill_books:
            self.logger.error("No skill books found. Run discover_book_ids.py first!")
            return {}
        
        # Prioritize skills if specified
        priority_skills = self.config.get('priority_skills', [])
        if priority_skills:
            priority_found = {k: v for k, v in skill_books.items() if k in priority_skills}
            other_skills = {k: v for k, v in skill_books.items() if k not in priority_skills}
            skill_books = {**priority_found, **other_skills}
            self.logger.info(f"Prioritized {len(priority_found)} skills")
        
        total_results = {
            'skills_processed': 0,
            'total_books': 0,
            'total_downloaded': 0,
            'total_failed': 0,
            'total_skipped': 0,
            'skill_results': {}
        }
        
        # Initialize progress tracker
        total_books = sum(len(books) for books in skill_books.values())
        self.progress_tracker.start_session(len(skill_books), total_books)
        self.progress_tracker.set_pending_skills(list(skill_books.keys()))
        
        self.logger.info(f"Starting download for {len(skill_books)} skills ({total_books:,} total books)")
        start_time = time.time()
        
        for i, (skill_name, books) in enumerate(skill_books.items(), 1):
            # Show progress bar
            skills_percent, books_percent = self.progress_tracker.get_progress_percentage()
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Progress: {i}/{len(skill_books)} skills ({skills_percent:.1f}%)")
            self.logger.info(f"Books: {len(self.downloaded_books):,}/{total_books:,} ({books_percent:.1f}%)")
            self.logger.info(f"ETA: {self.progress_tracker.get_eta_string()}")
            self.logger.info(f"{'='*60}")
            
            try:
                skill_results = self.download_books_for_skill(skill_name, books)
                total_results['skill_results'][skill_name] = skill_results
                total_results['skills_processed'] += 1
                total_results['total_books'] += skill_results['total']
                total_results['total_downloaded'] += skill_results['downloaded']
                total_results['total_failed'] += skill_results['failed']
                total_results['total_skipped'] += skill_results['skipped']
                
                # Save progress after each skill
                self._save_progress()
                
                # Create checkpoint every 10 skills
                if i % 10 == 0:
                    self.progress_tracker.create_checkpoint()
                
            except Exception as e:
                self.logger.error(f"Error processing skill {skill_name}: {e}")
                total_results['skill_results'][skill_name] = {'error': str(e)}
        
        # Mark session as completed
        self.progress_tracker.complete_session()
        
        # Final summary
        elapsed_time = time.time() - start_time
        self.logger.info(f"\n{'='*60}")
        self.logger.info("DOWNLOAD SUMMARY")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Skills processed: {total_results['skills_processed']}")
        self.logger.info(f"Total books found: {total_results['total_books']}")
        self.logger.info(f"Successfully downloaded: {total_results['total_downloaded']}")
        self.logger.info(f"Failed downloads: {total_results['total_failed']}")
        self.logger.info(f"Skipped (already downloaded): {total_results['total_skipped']}")
        self.logger.info(f"Total time: {elapsed_time/3600:.1f} hours")
        
        # Save final results
        results_file = 'download_results.json'
        with open(results_file, 'w') as f:
            json.dump(total_results, f, indent=2)
        self.logger.info(f"Detailed results saved to: {results_file}")
        
        # Show final progress
        self.progress_tracker.print_summary()
        
        return total_results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Download Books from Discovered IDs - Step 2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all discovered books
  python3 download_books.py
  
  # Download specific skills
  python3 download_books.py --skills "Python" "Machine Learning" "AI"
  
  # Use custom configuration
  python3 download_books.py --config my_config.json
  
  # Limit downloads per skill
  python3 download_books.py --max-books 20
        """
    )
    
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--skills', '-s', nargs='+', help='Specific skills to download (filters the list)')
    parser.add_argument('--max-books', type=int, help='Maximum books per skill')
    parser.add_argument('--workers', type=int, help='Number of concurrent download threads')
    parser.add_argument('--format', choices=['legacy', 'enhanced', 'kindle', 'dual'], 
                       help='EPUB format to generate')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be downloaded without actually downloading')
    
    args = parser.parse_args()
    
    # Initialize downloader
    downloader = BookDownloader(args.config)
    
    # Override config with command line arguments
    if args.max_books:
        downloader.config['max_books_per_skill'] = args.max_books
    if args.workers:
        downloader.config['max_workers'] = args.workers
    if args.format:
        downloader.config['epub_format'] = args.format
    if args.verbose:
        downloader.config['verbose'] = True
    
    if args.dry_run:
        print("DRY RUN MODE - No downloads will be performed")
        skill_books = downloader.load_skill_books(args.skills)
        
        total_books = sum(len(books) for books in skill_books.values())
        print(f"Would download {total_books:,} books across {len(skill_books)} skills:")
        
        for skill_name, books in list(skill_books.items())[:10]:  # Show first 10
            print(f"  - {skill_name}: {len(books):,} books")
        
        if len(skill_books) > 10:
            print(f"  ... and {len(skill_books) - 10} more skills")
        return
    
    try:
        # Start the download process
        results = downloader.download_all_books(args.skills)
        
        # Print final summary
        print(f"\n🎉 Download completed!")
        print(f"📚 Downloaded {results['total_downloaded']} books")
        print(f"📁 Organized in {results['skills_processed']} skill folders")
        print(f"⏱️  Check 'download_results.json' for detailed results")
        
    except KeyboardInterrupt:
        print("\n⚠️  Download interrupted by user")
        print("💾 Progress saved - you can resume later by running the script again")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

