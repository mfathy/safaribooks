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
import threading
from pathlib import Path
from typing import List, Dict, Set
import logging

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from oreilly_books.core import OreillyBooks
from oreilly_books.auth import AuthManager
from oreilly_books.display import Display
from progress_tracker import ProgressTracker
from progress_stats_writer import ProgressStatsWriter
from sound_notifier import SoundNotifier
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
        
        # Book IDs directory (only required for old format, not for new JSON file format)
        self.book_ids_dir = Path(self.config.get('book_ids_directory', 'book_ids'))
        # Note: Directory existence check is deferred to load_skill_books() - only needed for old format
        
        # Progress tracking
        self.progress_tracker = ProgressTracker(self.config['progress_file'], "download")
        self.downloaded_books: Set[str] = set(self.progress_tracker.data['completed_items'])
        self.failed_books: Dict[str, str] = dict(self.progress_tracker.data['failed_items'])
        
        # Progress stats writer for live updates
        self.stats_writer = ProgressStatsWriter(self.config.get('progress_stats_file', 'output/download_progress_live.txt'))
        
        # Sound notifier
        self.sound_notifier = SoundNotifier(
            enable_sound=self.config.get('enable_sound_notifications', True),
            sound_file=self.config.get('sound_file')
        )
        
        # Thread safety for parallel downloads (CRITICAL: prevents cookie race conditions)
        self.cookie_lock = threading.Lock()  # Protects cookie updates
        self.session_lock = threading.Lock()  # Protects session operations
        self.file_lock = threading.Lock()     # Protects file I/O (cookies.json)
        
        # Initialize shared session (CRITICAL FIX: reuse session to maintain fresh cookies)
        self.logger_with_component.info("Initializing shared authentication session...")
        self.display = Display("batch_download.log", PATH, component="BookDownloader")
        self.auth_manager = AuthManager(self.display)
        self.session = self.auth_manager.initialize_session()
        self.books_downloaded_since_save = 0
        
        # Consecutive failure tracking
        self.consecutive_failures = 0
        self.MAX_CONSECUTIVE_FAILURES = 10
        
        # Warn about parallel downloads if enabled
        max_workers = self.config.get('max_workers', 1)
        if max_workers > 1:
            self.logger_with_component.warning(f"⚠️  Parallel downloads disabled in current implementation (max_workers={max_workers})")
            self.logger_with_component.warning("    Reason: Shared session requires serial processing for cookie safety")
            self.logger_with_component.warning("    Downloads will run serially to prevent token conflicts")
            self.config['max_workers'] = 1  # Force serial for now
        
        self.logger_with_component.info("Authentication session established successfully")
    
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
            'priority_skills': [],
            'enable_sound_notifications': True,
            'sound_file': None,
            'progress_stats_file': 'output/download_progress_live.txt'
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
        
        # Unified format: [HH:MM:SS] [COMPONENT] [LEVEL] Message
        formatter = logging.Formatter(
            fmt='[%(asctime)s] [%(component)s] [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Prevent duplicate handlers
        logging.basicConfig(
            level=log_level,
            handlers=[]  # We'll add handlers manually
        )
        self.logger = logging.getLogger('BookDownloader')
        
        # Remove any existing handlers
        self.logger.handlers = []
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        self.logger.addHandler(console_handler)
        
        # Add component adapter for easy logging
        self.logger_with_component = logging.LoggerAdapter(
            self.logger, 
            {'component': 'BookDownloader'}
        )
    
    def _save_progress(self):
        """Save current download progress"""
        self.progress_tracker.save()
    
    def load_skill_books(self, skill_filter: List[str] = None) -> Dict[str, List[Dict]]:
        """Load discovered books for skills (old format: skill-based JSON files)"""
        # Check if book_ids directory exists (required for old format)
        if not self.book_ids_dir.exists():
            raise FileNotFoundError(f"Book IDs directory not found: {self.book_ids_dir}. Required for skill-based format.")
        
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
                self.logger_with_component.warning(f"Could not load skill file {skill_file}: {e}")
        
        self.logger_with_component.info(f"Loaded {len(skill_books)} skills with book data")
        return skill_books
    
    def load_books_from_json_file(self, json_file_path: str) -> Dict[str, List[Dict]]:
        """Load books from a single JSON file (new format: flat array with bookId)
        
        Args:
            json_file_path: Path to the JSON file containing books
            
        Returns:
            Dict with a single key "All Books" containing all books from the file
        """
        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                books_data = json.load(f)
            
            # Check if it's an array (new format) or object (old format)
            if isinstance(books_data, list):
                # New format: flat array of books
                books = books_data
                self.logger_with_component.info(f"Loaded {len(books)} books from new format JSON file")
                return {"All Books": books}
            elif isinstance(books_data, dict) and 'books' in books_data:
                # Old format: single skill object
                books = books_data.get('books', [])
                skill_name = books_data.get('skill_name', 'All Books')
                self.logger_with_component.info(f"Loaded {len(books)} books from old format JSON file (skill: {skill_name})")
                return {skill_name: books}
            else:
                raise ValueError(f"Unsupported JSON format in {json_file_path}")
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {json_file_path}: {e}")
        except Exception as e:
            self.logger_with_component.error(f"Error loading JSON file {json_file_path}: {e}")
            raise
    
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
        """Save current session cookies to file (keeps tokens fresh) - THREAD-SAFE"""
        with self.file_lock:  # Prevent simultaneous file writes
            try:
                with open(COOKIES_FILE, 'w') as f:
                    json.dump(self.session.cookies.get_dict(), f, indent=2)
                self.logger.debug("Cookies saved to file")
            except Exception as e:
                self.logger_with_component.warning(f"Failed to save cookies: {e}")
    
    def _update_cookies_from_headers(self, set_cookie_headers):
        """Update session cookies from Set-Cookie headers (like safaribooks.py does) - THREAD-SAFE
        
        This is CRITICAL for maintaining authentication - O'Reilly sends fresh tokens with each response.
        We update ALL cookies from Set-Cookie headers to keep the session authenticated.
        """
        with self.cookie_lock:  # CRITICAL: Only one worker can update cookies at a time
            for morsel in set_cookie_headers:
                try:
                    # Extract cookie key=value from the Set-Cookie header
                    # Format: "cookie_name=cookie_value; path=/; domain=.oreilly.com; max-age=3600"
                    cookie_part = morsel.split(";")[0].strip()
                    if "=" in cookie_part:
                        cookie_key, cookie_value = cookie_part.split("=", 1)
                        self.session.cookies.set(cookie_key, cookie_value)
                        self.logger.debug(f"Updated cookie: {cookie_key} [thread-safe]")
                except Exception as e:
                    # Log but don't fail - some cookies might have unusual formats
                    self.logger.debug(f"Failed to parse cookie header '{morsel[:50]}...': {e}")
    
    def _check_epub_exists(self, search_dir: Path, book_id: str, epub_format: str) -> bool:
        """Check if EPUB file(s) already exist for this book.
        
        Args:
            search_dir: Directory to search in (could be skill_dir or book_folder)
            book_id: Book ID to search for
            epub_format: Format to check ('dual', 'enhanced', 'kindle', 'legacy')
        """
        # First, try to find book folder if searching in skill_dir
        # If search_dir already contains book_id in its name, it's likely the book folder
        is_book_folder = f"({book_id})" in search_dir.name or book_id in search_dir.name
        
        if is_book_folder:
            # We're already in the book folder - check for any EPUB files
            epub_files = list(search_dir.glob("*.epub"))
        else:
            # We're in skill_dir - look for book folder first, then check EPUBs
            book_folder = self._find_book_folder(search_dir, book_id)
            if not book_folder:
                return False
            epub_files = list(book_folder.glob("*.epub"))
        
        if not epub_files:
            return False
        
        # Check format-specific requirements
        if epub_format == 'dual':
            # Need both standard and Kindle versions
            has_standard = any('Kindle' not in f.name and '_EBOK' not in f.name for f in epub_files)
            has_kindle = any('Kindle' in f.name or '_EBOK' in f.name for f in epub_files)
            return has_standard and has_kindle
        elif epub_format == 'kindle':
            # Need Kindle version
            return any('Kindle' in f.name or '_EBOK' in f.name for f in epub_files)
        else:
            # enhanced or legacy - need standard version (non-Kindle)
            return any('Kindle' not in f.name and '_EBOK' not in f.name for f in epub_files)
    
    def _find_book_folder(self, skill_dir: Path, book_id: str):
        """Find the book folder by searching for folders containing the book ID"""
        # Try patterns: "Book Title (book_id)" or "Book Title book_id"
        patterns = [
            f"*({book_id})*",
            f"*{book_id}*"
        ]
        
        for pattern in patterns:
            matches = list(skill_dir.glob(pattern))
            # Filter to only directories
            dir_matches = [m for m in matches if m.is_dir()]
            if dir_matches:
                # Return the first match (should be unique)
                return dir_matches[0]
        
        return None
    
    def _check_book_complete(self, skill_dir: Path, book_id: str, epub_format: str) -> tuple[bool, str]:
        """Check if a book is completely downloaded and EPUB generation is complete.
        
        This method verifies:
        1. Book folder exists
        2. OEBPS folder exists (indicates content download is complete)
        3. EPUB file(s) exist based on format (indicates EPUB generation is complete)
        
        Returns:
            tuple[bool, str]: (is_complete, reason)
            - is_complete: True if book is fully downloaded and EPUB generated
            - reason: Description of why it's complete or incomplete
        """
        # Step 1: Find the book folder
        book_folder = self._find_book_folder(skill_dir, book_id)
        if not book_folder:
            return False, "Book folder not found"
        
        # Step 2: Check if download is complete (OEBPS folder exists and has content)
        oebps_dir = book_folder / "OEBPS"
        if not oebps_dir.exists() or not oebps_dir.is_dir():
            return False, "OEBPS folder missing (download incomplete)"
        
        # Check if OEBPS has content (at least content.opf should exist)
        content_opf = oebps_dir / "content.opf"
        if not content_opf.exists():
            return False, "OEBPS/content.opf missing (download incomplete)"
        
        # Step 3: Check if EPUB generation is complete
        epub_complete = self._check_epub_exists(book_folder, book_id, epub_format)
        if not epub_complete:
            return False, f"EPUB file(s) missing for format '{epub_format}' (EPUB generation incomplete)"
        
        # All checks passed - book is complete
        return True, "Book download and EPUB generation complete"
    
    def download_single_book(self, book_info: Dict, skill_name: str, skill_dir: Path) -> tuple[bool, bool]:
        """Download a single book using shared session (FIXED: no more session recreation)
        
        Returns:
            tuple[bool, bool]: (success, was_downloaded)
            - success: True if operation succeeded (skip or download), False if failed
            - was_downloaded: True if actual download occurred, False if skipped
        """
        # Support both formats: 'id' (old format) and 'bookId' (new format)
        book_id_raw = book_info.get('id') or book_info.get('bookId', '')
        book_id = self._extract_book_id(book_id_raw)
        book_title = book_info.get('title', f'Book {book_id}')
        
        # Check if already downloaded (unless force_redownload is enabled)
        tracking_id = book_id_raw if book_id_raw else book_id
        
        if not self.config.get('force_redownload', False):
            # First check if EPUB files exist
            if self._check_epub_exists(skill_dir, book_id, self.config['epub_format']):
                self.logger_with_component.info(f"⏭️  Skipping {book_title} (EPUB already exists)")
                # Reset consecutive failures on skip (successful operation)
                self.consecutive_failures = 0
                # Mark as downloaded in progress tracker
                if tracking_id not in self.downloaded_books:
                    self.downloaded_books.add(tracking_id)
                    self.progress_tracker.add_completed_item(tracking_id)
                return True, False  # success=True, was_downloaded=False
            
            # Then check progress tracker
            if tracking_id in self.downloaded_books or book_id in self.downloaded_books:
                self.logger_with_component.info(f"⏭️  Skipping {book_title} (already downloaded)")
                # Reset consecutive failures on skip (successful operation)
                self.consecutive_failures = 0
                # Update progress stats for skipped book
                self.stats_writer.update_book_completed(was_downloaded=False, was_successful=True)
                return True, False  # success=True, was_downloaded=False
        else:
            # Force re-download mode: Check if book is complete before re-downloading
            is_complete, reason = self._check_book_complete(skill_dir, book_id, self.config['epub_format'])
            if is_complete:
                self.logger_with_component.info(f"✅ Skipping {book_title} (complete: {reason})")
                # Reset consecutive failures on skip (successful operation)
                self.consecutive_failures = 0
                # Mark as downloaded in progress tracker
                if tracking_id not in self.downloaded_books:
                    self.downloaded_books.add(tracking_id)
                    self.progress_tracker.add_completed_item(tracking_id)
                # Update progress stats for skipped book
                self.stats_writer.update_book_completed(was_downloaded=False, was_successful=True)
                return True, False  # success=True, was_downloaded=False
            else:
                self.logger_with_component.info(f"🔄 Force re-downloading: {book_title} (incomplete: {reason})")
        
        self.logger_with_component.info(f"📚 Downloading: {book_title} (ID: {book_id})")
        
        try:
            # Import the custom exception
            from oreilly_books.exceptions import BookDownloadError
            
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
                    self.logger_with_component.info("Generating dual EPUB files (Standard + Kindle)...")
                    enhanced_epub_generator.create_enhanced_epub(api_url, args.bookid, PATH, is_kindle=False)
                    enhanced_epub_generator.create_enhanced_epub(api_url, args.bookid, PATH, is_kindle=True)
                elif args.enhanced or args.kindle:
                    epub_type = "Kindle-optimized" if args.kindle else "Standard"
                    self.logger_with_component.info(f"Generating {epub_type} EPUB 3.3...")
                    enhanced_epub_generator.create_enhanced_epub(api_url, args.bookid, PATH, is_kindle=args.kindle)
                else:
                    self.logger_with_component.info("Generating legacy EPUB 2.0...")
                    epub_generator.create_epub(api_url, args.bookid, PATH)
                
                # Mark as downloaded and reset consecutive failures on success
                self.downloaded_books.add(tracking_id)
                self.progress_tracker.add_completed_item(tracking_id)
                self.consecutive_failures = 0  # Reset on success
                
                # Update progress stats and play sound notification
                self.stats_writer.update_book_completed(was_downloaded=True, was_successful=True)
                self.sound_notifier.play_notification()
                
                # Save cookies every N books to keep tokens fresh (configurable)
                self.books_downloaded_since_save += 1
                token_save_interval = self.config.get('token_save_interval', 5)
                if self.books_downloaded_since_save >= token_save_interval:
                    self._save_cookies()
                    self.logger_with_component.info(f"💾 Saved authentication cookies (keeps tokens fresh)")
                    self.books_downloaded_since_save = 0
                
                self.logger_with_component.info(f"✅ Successfully downloaded: {book_title}")
                return True, True  # success=True, was_downloaded=True
                
            finally:
                # Restore environment
                if original_path_env:
                    os.environ['OREILLY_OUTPUT_PATH'] = original_path_env
                elif 'OREILLY_OUTPUT_PATH' in os.environ:
                    del os.environ['OREILLY_OUTPUT_PATH']
                
        except BookDownloadError as e:
            # Handle book-specific download errors gracefully
            self.consecutive_failures += 1
            error_msg = f"Book download error: {e}"
            self.logger_with_component.error(f"❌ {error_msg}")
            self.failed_books[tracking_id] = error_msg
            self.progress_tracker.add_failed_item(tracking_id, error_msg)
            # Update progress stats for failed book
            self.stats_writer.update_book_completed(was_downloaded=True, was_successful=False)
            return False, True  # success=False, was_downloaded=True (attempted download)
            
        except Exception as e:
            # Handle other unexpected errors
            self.consecutive_failures += 1
            self.logger_with_component.error(f"❌ Failed to download {book_title}: {e}")
            import traceback
            if self.config.get('verbose', False):
                self.logger_with_component.debug(traceback.format_exc())
            self.failed_books[tracking_id] = str(e)
            self.progress_tracker.add_failed_item(tracking_id, str(e))
            # Update progress stats for failed book
            self.stats_writer.update_book_completed(was_downloaded=True, was_successful=False)
            return False, True  # success=False, was_downloaded=True (attempted download)
    
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
        self.logger_with_component.info(f"\n{'='*60}")
        self.logger_with_component.info(f"Downloading books for skill: {skill_name}")
        self.logger_with_component.info(f"{'='*60}")
        
        # Create skill directory
        skill_dir = self._get_skill_directory(skill_name)
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # Update progress stats with current skill
        self.stats_writer.update_current_skill(skill_name)
        
        # Limit books if specified (but not when loading from JSON file with "All Books")
        # When using JSON file format, we want to process all books, not limit them
        max_books = self.config.get('max_books_per_skill', 1000)
        # Only apply limit if it's not the "All Books" skill from JSON file
        # and if max_books is not None/0 (which means no limit)
        if skill_name != "All Books" and max_books and max_books > 0 and len(books) > max_books:
            self.logger_with_component.info(f"Limiting {skill_name} to {max_books} books (found {len(books)})")
            books = books[:max_books]
        elif skill_name == "All Books" and max_books and max_books > 0 and len(books) > max_books:
            self.logger_with_component.warning(f"⚠️  Found {len(books)} books but max_books_per_skill is {max_books}")
            self.logger_with_component.warning(f"   Processing all {len(books)} books (limit ignored for 'All Books' from JSON file)")
        
        self.logger_with_component.info(f"Downloading {len(books)} books for {skill_name}")
        
        # Update progress tracker
        self.progress_tracker.update_current_skill(skill_name, 0, len(books))
        
        # Download books serially
        results = {'total': len(books), 'downloaded': 0, 'failed': 0, 'skipped': 0}
        
        for i, book_info in enumerate(books, 1):
            self.logger_with_component.info(f"  [{i}/{len(books)}] Processing...")
            
            success, was_downloaded = self.download_single_book(book_info, skill_name, skill_dir)
            if success:
                if was_downloaded:
                    results['downloaded'] += 1
                else:
                    results['skipped'] += 1
            else:
                results['failed'] += 1
                
                # Check for consecutive failure threshold
                if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    self.logger_with_component.error(f"🛑 STOPPING: {self.consecutive_failures} consecutive failures reached (threshold: {self.MAX_CONSECUTIVE_FAILURES})")
                    self.logger_with_component.error("This may indicate a systematic issue (authentication, network, or server problems)")
                    self.logger_with_component.error("Please check your authentication and try again later")
                    raise Exception(f"Consecutive failure threshold reached: {self.consecutive_failures} failures")
            
            # Save progress after each book
            self._save_progress()
            
            # Add delay between downloads (rate limiting) - only when actual download occurred
            if was_downloaded and i < len(books):  # Don't delay after the last book
                time.sleep(self.config['download_delay'])
        
        # Mark skill as completed
        self.progress_tracker.complete_skill(skill_name)
        
        # Update progress stats with skill completion
        self.stats_writer.update_skill_completed(skill_name, results)
        
        self.logger_with_component.info(f"Completed {skill_name}: {results}")
        return results
    
    def download_all_books(self, skill_filter: List[str] = None, json_file: str = None) -> Dict[str, Dict]:
        """Download books for all skills (serial processing)
        
        Args:
            skill_filter: Optional list of skill names to filter (only used with old format)
            json_file: Optional path to JSON file (new format). If provided, loads from file instead of skill directories
        """
        if json_file:
            # Load from single JSON file (new format)
            skill_books = self.load_books_from_json_file(json_file)
            # When using JSON file, ignore skill_filter (download all books)
            if skill_filter:
                self.logger_with_component.warning("Skill filter ignored when using JSON file - downloading all books")
        else:
            # Load from skill directories (old format)
            skill_books = self.load_skill_books(skill_filter)
        
        if not skill_books:
            if json_file:
                self.logger_with_component.error(f"No books found in JSON file: {json_file}")
            else:
                self.logger_with_component.error("No skill books found. Run discover_book_ids.py first!")
            return {}
        
        # Prioritize skills if specified
        priority_skills = self.config.get('priority_skills', [])
        if priority_skills:
            priority_found = {k: v for k, v in skill_books.items() if k in priority_skills}
            other_skills = {k: v for k, v in skill_books.items() if k not in priority_skills}
            skill_books = {**priority_found, **other_skills}
            self.logger_with_component.info(f"Prioritized {len(priority_found)} skills")
        
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
        
        # Initialize progress stats writer
        self.stats_writer.update_session_start(len(skill_books), total_books)
        
        self.logger_with_component.info(f"Starting download for {len(skill_books)} skills ({total_books:,} total books)")
        start_time = time.time()
        
        for i, (skill_name, books) in enumerate(skill_books.items(), 1):
            # Show progress bar
            skills_percent, books_percent = self.progress_tracker.get_progress_percentage()
            self.logger_with_component.info(f"\n{'='*60}")
            self.logger_with_component.info(f"Progress: {i}/{len(skill_books)} skills ({skills_percent:.1f}%)")
            self.logger_with_component.info(f"Books: {len(self.downloaded_books):,}/{total_books:,} ({books_percent:.1f}%)")
            self.logger_with_component.info(f"ETA: {self.progress_tracker.get_eta_string()}")
            self.logger_with_component.info(f"{'='*60}")
            
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
                if "Consecutive failure threshold reached" in str(e):
                    # Handle consecutive failure threshold
                    self.logger_with_component.error(f"🛑 CONSECUTIVE FAILURE THRESHOLD REACHED")
                    self.logger_with_component.error(f"Stopping download process due to {self.consecutive_failures} consecutive failures")
                    self.logger_with_component.error("This indicates a systematic issue that needs attention")
                    
                    # Save progress and cookies before stopping
                    self._save_progress()
                    self._save_cookies()
                    
                    # Add failure summary to results
                    total_results['skill_results'][skill_name] = {
                        'error': f"Consecutive failure threshold reached: {self.consecutive_failures} failures",
                        'consecutive_failures': self.consecutive_failures,
                        'stopped_due_to_threshold': True
                    }
                    
                    # Log final summary
                    self.logger_with_component.error(f"\n{'='*60}")
                    self.logger_with_component.error("DOWNLOAD STOPPED DUE TO CONSECUTIVE FAILURES")
                    self.logger_with_component.error(f"{'='*60}")
                    self.logger_with_component.error(f"Consecutive failures: {self.consecutive_failures}")
                    self.logger_with_component.error(f"Total books processed: {len(self.downloaded_books)}")
                    self.logger_with_component.error(f"Total failed books: {len(self.failed_books)}")
                    self.logger_with_component.error("Please check your authentication and network connection")
                    self.logger_with_component.error("You can resume by running the script again")
                    
                    break  # Stop processing more skills
                else:
                    # Handle other skill processing errors
                    self.logger_with_component.error(f"Error processing skill {skill_name}: {e}")
                    total_results['skill_results'][skill_name] = {'error': str(e)}
        
        # Mark session as completed
        self.progress_tracker.complete_session()
        
        # Finalize progress stats
        self.stats_writer.finalize(total_results)
        
        # Save final cookie state (CRITICAL: persist fresh tokens)
        self._save_cookies()
        self.logger_with_component.info("Session cookies saved to file")
        
        # Final summary
        elapsed_time = time.time() - start_time
        self.logger_with_component.info(f"\n{'='*60}")
        self.logger_with_component.info("DOWNLOAD SUMMARY")
        self.logger_with_component.info(f"{'='*60}")
        self.logger_with_component.info(f"Skills processed: {total_results['skills_processed']}")
        self.logger_with_component.info(f"Total books found: {total_results['total_books']}")
        self.logger_with_component.info(f"Successfully downloaded: {total_results['total_downloaded']}")
        self.logger_with_component.info(f"Failed downloads: {total_results['total_failed']}")
        self.logger_with_component.info(f"Skipped (already downloaded): {total_results['total_skipped']}")
        self.logger_with_component.info(f"Total time: {elapsed_time/3600:.1f} hours")
        
        # Save final results
        results_file = 'output/download_results.json'
        os.makedirs('output', exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(total_results, f, indent=2)
        self.logger_with_component.info(f"Detailed results saved to: {results_file}")
        
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
    parser.add_argument('--skills', '-s', nargs='+', help='Specific skills to download (filters the list, only for old format)')
    parser.add_argument('--json-file', '-j', help='Path to JSON file with books (new format). If provided, downloads all books from this file instead of skill directories')
    parser.add_argument('--max-books', type=int, help='Maximum books per skill')
    parser.add_argument('--format', choices=['legacy', 'enhanced', 'kindle', 'dual'], 
                       help='EPUB format to generate')
    parser.add_argument('--force', '-f', action='store_true', 
                       help='Force re-download books even if EPUB exists')
    parser.add_argument('--token-save-interval', type=int, 
                       help='Save authentication cookies after N books (default: 5)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be downloaded without actually downloading')
    parser.add_argument('--no-sound', action='store_true', help='Disable sound notifications')
    parser.add_argument('--sound-file', help='Path to custom sound file for notifications')
    
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
    if args.no_sound:
        downloader.config['enable_sound_notifications'] = False
    if args.sound_file:
        downloader.config['sound_file'] = args.sound_file
    
    if args.dry_run:
        print("DRY RUN MODE - No downloads will be performed")
        if args.json_file:
            skill_books = downloader.load_books_from_json_file(args.json_file)
        else:
            skill_books = downloader.load_skill_books(args.skills)
        
        total_books = sum(len(books) for books in skill_books.values())
        print(f"Would download {total_books:,} books across {len(skill_books)} skills:")
        
        for skill_name, books in list(skill_books.items())[:10]:  # Show first 10
            print(f"  - {skill_name}: {len(books):,} books")
        
        if len(skill_books) > 10:
            print(f"  ... and {len(skill_books) - 10} more skills")
        
        # Show progress stats file info
        stats_file = downloader.config.get('progress_stats_file', 'output/download_progress_live.txt')
        print(f"\n📊 Progress stats will be written to: {stats_file}")
        print(f"   Run 'tail -f {stats_file}' in another terminal to monitor progress")
        return
    
    try:
        # Show progress stats file info
        stats_file = downloader.config.get('progress_stats_file', 'output/download_progress_live.txt')
        print(f"📊 Progress stats will be written to: {stats_file}")
        print(f"   Run 'tail -f {stats_file}' in another terminal to monitor progress")
        print()
        
        # Start the download process (serial)
        results = downloader.download_all_books(args.skills, args.json_file)
        
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

