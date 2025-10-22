#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Book Downloader Script - Step 2
Downloads actual books from previously discovered book IDs
Uses a shared session to avoid token invalidation
"""

import os
import sys
import json
import time
import argparse
import re
from pathlib import Path
from typing import List, Dict, Set
import logging

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from oreilly_books.core import OreillyBooks
from oreilly_books.auth import AuthManager
from oreilly_books.display import Display
from progress_tracker import ProgressTracker
from config import COOKIES_FILE, PATH


class BookDownloader:
    """Downloads books from discovered book IDs using serial processing with shared session"""
    
    COOKIE_FLOAT_MAX_AGE_PATTERN = re.compile(r'(max-age=\d*\.\d*)', re.IGNORECASE)
    
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
        
        # Progress tracking
        self.progress_tracker = ProgressTracker(self.config['progress_file'], "download")
        self.downloaded_books: Set[str] = set(self.progress_tracker.data['completed_items'])
        self.failed_books: Dict[str, str] = dict(self.progress_tracker.data['failed_items'])
        
        # Initialize shared session (CRITICAL FIX: reuse session to maintain fresh cookies)
        self.logger.info("Initializing shared authentication session...")
        self.display = Display("batch_download.log", PATH)
        self.auth_manager = AuthManager(self.display)
        self.session = self.auth_manager.initialize_session()
        self.books_downloaded_since_save = 0
        self.logger.info("Authentication session established successfully")
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'base_directory': 'books_by_skills',
            'book_ids_directory': 'book_ids',
            'max_books_per_skill': 1000,
            'download_delay': 3,
            'epub_format': 'dual',
            'resume': True,
            'force_redownload': False,
            'token_save_interval': 5,
            'progress_file': 'output/download_progress.json',
            'log_file': 'logs/book_downloader.log',
            'verbose': False,
            'exclude_skills': [],
            'priority_skills': []
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
        
        # Ensure logs directory exists
        log_file = self.config.get('log_file', 'logs/book_downloader.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('BookDownloader')
    
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
        """Sanitize skill name for use as directory name and convert to PascalCase with spaces"""
        # First remove invalid characters
        sanitized = skill_name.strip()
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            sanitized = sanitized.replace(char, ' ')
        
        # Convert to PascalCase with spaces
        # Split by common separators
        words = sanitized.replace('_', ' ').replace('-', ' ').split()
        
        # Capitalize each word properly
        pascal_words = []
        for word in words:
            # Handle special cases like "AI", "ML", "API", etc.
            if word.upper() in ['AI', 'ML', 'API', 'UI', 'UX', 'SQL', 'CSS', 'HTML', 'JS', 'AWS', 'GCP']:
                pascal_words.append(word.upper())
            # Handle &, and, etc.
            elif word.lower() in ['&', 'and', 'or', 'of', 'the', 'in', 'on', 'at', 'to', 'for']:
                # Keep conjunctions and prepositions lowercase unless first word
                if len(pascal_words) == 0:
                    pascal_words.append(word.capitalize())
                else:
                    pascal_words.append(word.lower())
            else:
                # Regular word - capitalize first letter
                pascal_words.append(word.capitalize())
        
        return ' '.join(pascal_words)
    
    def _get_skill_directory(self, skill_name: str) -> Path:
        """Get the directory path for a skill"""
        sanitized_name = self._sanitize_skill_name(skill_name)
        return self.base_dir / sanitized_name
    
    def _extract_book_id(self, book_id_raw: str) -> str:
        """Extract numeric book ID from various formats"""
        if isinstance(book_id_raw, str):
            if book_id_raw.startswith('http'):
                # Extract ISBN from URL like "https://www.safaribooksonline.com/api/v1/book/9781234567890/"
                import re
                match = re.search(r'/book/(\d+)/', book_id_raw)
                if match:
                    return match.group(1)
                else:
                    # Try to get the last numeric segment
                    parts = [p for p in book_id_raw.split('/') if p and p.isdigit()]
                    return parts[-1] if parts else book_id_raw
            else:
                return book_id_raw
        else:
            return str(book_id_raw)
    
    def _save_cookies(self):
        """Save current session cookies to file (keeps tokens fresh)"""
        try:
            with open(COOKIES_FILE, 'w') as f:
                json.dump(self.session.cookies.get_dict(), f, indent=2)
            self.logger.debug("Cookies saved to file")
        except Exception as e:
            self.logger.warning(f"Failed to save cookies: {e}")
    
    def _update_cookies_from_headers(self, set_cookie_headers):
        """Update session cookies from Set-Cookie headers (like safaribooks.py does)"""
        for morsel in set_cookie_headers:
            # Handle Float 'max-age' Cookie (O'Reilly sometimes sends float values)
            if self.COOKIE_FLOAT_MAX_AGE_PATTERN.search(morsel):
                try:
                    cookie_key, cookie_value = morsel.split(";")[0].split("=", 1)
                    self.session.cookies.set(cookie_key, cookie_value)
                    self.logger.debug(f"Updated cookie: {cookie_key}")
                except Exception as e:
                    self.logger.debug(f"Failed to parse cookie: {e}")
    
    def _check_epub_exists(self, skill_dir: Path, book_id: str, epub_format: str) -> bool:
        """Check if EPUB file(s) already exist for this book"""
        # Look for any EPUB files containing the book ID
        epub_patterns = [
            f"*({book_id})*.epub",
            f"*{book_id}*.epub"
        ]
        
        for pattern in epub_patterns:
            if list(skill_dir.glob(pattern)):
                return True
        
        # Check for specific format files
        if epub_format in ['dual', 'kindle']:
            # Check for Kindle format: *_EBOK.epub
            if list(skill_dir.glob(f"*({book_id})*_EBOK.epub")) or list(skill_dir.glob(f"*{book_id}*_EBOK.epub")):
                if epub_format == 'kindle':
                    return True
        
        if epub_format in ['dual', 'enhanced', 'legacy']:
            # Check for standard EPUB (non-EBOK)
            for epub_file in skill_dir.glob(f"*({book_id})*.epub"):
                if '_EBOK' not in epub_file.name:
                    if epub_format != 'dual':
                        return True
            for epub_file in skill_dir.glob(f"*{book_id}*.epub"):
                if '_EBOK' not in epub_file.name:
                    if epub_format != 'dual':
                        return True
        
        # For dual format, check if both exist
        if epub_format == 'dual':
            has_standard = False
            has_kindle = False
            
            for epub_file in skill_dir.glob(f"*({book_id})*.epub"):
                if '_EBOK' in epub_file.name:
                    has_kindle = True
                else:
                    has_standard = True
            
            for epub_file in skill_dir.glob(f"*{book_id}*.epub"):
                if '_EBOK' in epub_file.name:
                    has_kindle = True
                else:
                    has_standard = True
            
            return has_standard and has_kindle
        
        return False
    
    def download_single_book(self, book_info: Dict, skill_name: str, skill_dir: Path) -> bool:
        """Download a single book using shared session (FIXED: no more session recreation)"""
        book_id_raw = book_info.get('id', '')
        book_id = self._extract_book_id(book_id_raw)
        book_title = book_info.get('title', f'Book {book_id}')
        
        # Check if already downloaded (unless force_redownload is enabled)
        tracking_id = book_id_raw if book_id_raw else book_id
        
        if not self.config.get('force_redownload', False):
            # First check if EPUB files exist
            if self._check_epub_exists(skill_dir, book_id, self.config['epub_format']):
                self.logger.info(f"⏭️  Skipping {book_title} (EPUB already exists)")
                # Mark as downloaded in progress tracker
                if tracking_id not in self.downloaded_books:
                    self.downloaded_books.add(tracking_id)
                    self.progress_tracker.add_completed_item(tracking_id)
                return True
            
            # Then check progress tracker
            if tracking_id in self.downloaded_books or book_id in self.downloaded_books:
                self.logger.info(f"⏭️  Skipping {book_title} (already downloaded)")
                return True
        else:
            self.logger.info(f"🔄 Force re-downloading: {book_title}")
        
        self.logger.info(f"📚 Downloading: {book_title} (ID: {book_id})")
        
        try:
            # Ensure skill directory exists
            skill_dir.mkdir(parents=True, exist_ok=True)
            
            # Create args for OreillyBooks
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
            
            # Set output path to skill directory
            original_path_env = os.environ.get('OREILLY_OUTPUT_PATH')
            os.environ['OREILLY_OUTPUT_PATH'] = str(skill_dir.absolute())
            
            try:
                # CRITICAL FIX: Use the existing shared session instead of creating new instance
                # This maintains cookie freshness across downloads
                book_downloader_instance = OreillyBooks.__new__(OreillyBooks)
                book_downloader_instance.args = args
                book_downloader_instance.display = self.display
                
                # Import required modules for the download process
                from oreilly_books.download import BookDownloader as InternalDownloader
                from oreilly_books.epub_legacy import LegacyEpubGenerator
                from oreilly_books.epub_enhanced import EnhancedEpubGenerator
                from config import SAFARI_BASE_URL, BASE_01_HTML, KINDLE_HTML, BASE_02_HTML
                from html import escape
                
                # Set up the book downloader with our shared session and cookie update callback
                internal_downloader = InternalDownloader(
                    self.session, 
                    self.display, 
                    args.bookid,
                    cookie_update_callback=self._update_cookies_from_headers  # CRITICAL: Updates cookies after every request
                )
                
                # Get book info and chapters
                book_info_data = internal_downloader.get_book_info()
                book_chapters = internal_downloader.get_book_chapters()
                
                # Setup book paths
                book_title_clean = "".join(self._escape_dirname(book_info_data.get("title", "Unknown Book")).split(",")[:2]) + f" ({args.bookid})"
                internal_downloader.BOOK_PATH = os.path.join(str(skill_dir.absolute()), book_title_clean)
                
                os.makedirs(internal_downloader.BOOK_PATH, exist_ok=True)
                os.makedirs(os.path.join(internal_downloader.BOOK_PATH, "OEBPS"), exist_ok=True)
                os.makedirs(os.path.join(internal_downloader.BOOK_PATH, "OEBPS", "Images"), exist_ok=True)
                os.makedirs(os.path.join(internal_downloader.BOOK_PATH, "OEBPS", "Styles"), exist_ok=True)
                
                internal_downloader.css_path = os.path.join(internal_downloader.BOOK_PATH, "OEBPS", "Styles")
                internal_downloader.images_path = os.path.join(internal_downloader.BOOK_PATH, "OEBPS", "Images")
                internal_downloader.base_url = book_info_data.get("web_url", "")
                
                # Initialize EPUB generators
                epub_generator = LegacyEpubGenerator(
                    self.session, self.display, book_info_data, book_chapters,
                    internal_downloader.BOOK_PATH, internal_downloader.css_path, 
                    internal_downloader.images_path
                )
                
                enhanced_epub_generator = EnhancedEpubGenerator(
                    self.session, self.display, book_info_data, book_chapters,
                    internal_downloader.BOOK_PATH, internal_downloader.css_path, 
                    internal_downloader.images_path
                )
                
                # Download content
                chapters_queue = book_chapters[:]
                base_html = BASE_01_HTML + (KINDLE_HTML if not args.kindle else "") + BASE_02_HTML
                
                internal_downloader.download_chapters(chapters_queue, base_html)
                
                # Handle cover if not found
                if not internal_downloader.cover:
                    internal_downloader.cover = internal_downloader.get_default_cover() if "cover" in book_info_data else False
                
                # Download CSS and images
                epub_generator.collect_css(internal_downloader.css)
                epub_generator.collect_images(internal_downloader.images)
                
                # Generate EPUB
                api_url = f"{SAFARI_BASE_URL}/api/v1/book/{args.bookid}/"
                
                if args.dual:
                    enhanced_epub_generator.create_enhanced_epub(api_url, args.bookid, PATH, is_kindle=False)
                    enhanced_epub_generator.create_enhanced_epub(api_url, args.bookid, PATH, is_kindle=True)
                elif args.enhanced or args.kindle:
                    enhanced_epub_generator.create_enhanced_epub(api_url, args.bookid, PATH, is_kindle=args.kindle)
                else:
                    epub_generator.create_epub(api_url, args.bookid, PATH)
                
                # Mark as downloaded
                self.downloaded_books.add(tracking_id)
                self.progress_tracker.add_completed_item(tracking_id)
                
                # Save cookies every N books to keep tokens fresh (configurable)
                self.books_downloaded_since_save += 1
                token_save_interval = self.config.get('token_save_interval', 5)
                if self.books_downloaded_since_save >= token_save_interval:
                    self._save_cookies()
                    self.logger.info(f"💾 Saved authentication cookies (keeps tokens fresh)")
                    self.books_downloaded_since_save = 0
                
                self.logger.info(f"✅ Successfully downloaded: {book_title}")
                return True
                
            finally:
                # Restore environment
                if original_path_env:
                    os.environ['OREILLY_OUTPUT_PATH'] = original_path_env
                elif 'OREILLY_OUTPUT_PATH' in os.environ:
                    del os.environ['OREILLY_OUTPUT_PATH']
                
        except Exception as e:
            self.logger.error(f"❌ Failed to download {book_title}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            self.failed_books[tracking_id] = str(e)
            self.progress_tracker.add_failed_item(tracking_id, str(e))
            return False
    
    @staticmethod
    def _escape_dirname(dirname, clean_space=False):
        """Escape directory name for filesystem compatibility"""
        if ":" in dirname:
            if "win" in sys.platform:
                dirname = dirname.replace(":", ",")
            else:
                dirname = dirname.split(":")[0]
        
        for ch in ['~', '#', '%', '&', '*', '{', '}', '\\', '<', '>', '?', '/', '`', '\'', '"', '|', '+', ':']:
            if ch in dirname:
                dirname = dirname.replace(ch, "_")
        
        return dirname if not clean_space else dirname.replace(" ", "")
    
    def download_books_for_skill(self, skill_name: str, books: List[Dict]) -> Dict[str, int]:
        """Download all books for a specific skill (serial processing)"""
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
        
        # Download books serially
        results = {'total': len(books), 'downloaded': 0, 'failed': 0, 'skipped': 0}
        
        for i, book_info in enumerate(books, 1):
            self.logger.info(f"  [{i}/{len(books)}] Processing...")
            
            success = self.download_single_book(book_info, skill_name, skill_dir)
            if success:
                results['downloaded'] += 1
            else:
                results['failed'] += 1
            
            # Save progress after each book
            self._save_progress()
            
            # Add delay between downloads (rate limiting)
            if i < len(books):  # Don't delay after the last book
                time.sleep(self.config['download_delay'])
        
        # Mark skill as completed
        self.progress_tracker.complete_skill(skill_name)
        
        self.logger.info(f"Completed {skill_name}: {results}")
        return results
    
    def download_all_books(self, skill_filter: List[str] = None) -> Dict[str, Dict]:
        """Download books for all skills (serial processing)"""
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
        
        # Save final cookie state (CRITICAL: persist fresh tokens)
        self._save_cookies()
        self.logger.info("Session cookies saved to file")
        
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
        results_file = 'output/download_results.json'
        os.makedirs('output', exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(total_results, f, indent=2)
        self.logger.info(f"Detailed results saved to: {results_file}")
        
        # Show final progress
        self.progress_tracker.print_summary()
        
        return total_results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Download Books from Discovered IDs - Step 2 (Serial Processing)",
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
  
  # Generate dual format (Standard + Kindle)
  python3 download_books.py --format dual
        """
    )
    
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--skills', '-s', nargs='+', help='Specific skills to download (filters the list)')
    parser.add_argument('--max-books', type=int, help='Maximum books per skill')
    parser.add_argument('--format', choices=['legacy', 'enhanced', 'kindle', 'dual'], 
                       help='EPUB format to generate')
    parser.add_argument('--force', '-f', action='store_true', 
                       help='Force re-download books even if EPUB exists')
    parser.add_argument('--token-save-interval', type=int, 
                       help='Save authentication cookies after N books (default: 5)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be downloaded without actually downloading')
    
    args = parser.parse_args()
    
    # Initialize downloader
    downloader = BookDownloader(args.config)
    
    # Override config with command line arguments
    if args.max_books:
        downloader.config['max_books_per_skill'] = args.max_books
    if args.format:
        downloader.config['epub_format'] = args.format
    if args.force:
        downloader.config['force_redownload'] = True
    if args.token_save_interval:
        downloader.config['token_save_interval'] = args.token_save_interval
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
        # Start the download process (serial)
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

