#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
O'Reilly Books Automation Script
Downloads all books for favorite skills and organizes them by skill folders
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

from oreilly_parser.oreilly_books_parser import search_oreilly_learning_api_with_pagination, load_cookies
from oreilly_books import OreillyBooks


class SkillBookDownloader:
    """Automated downloader for books organized by skills"""
    
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        self.setup_logging()
        
        # Load authentication cookies
        self.cookies = load_cookies()
        if not self.cookies:
            self.logger.warning("No authentication cookies found. Some content may not be accessible.")
        
        # Create base directory structure
        self.base_dir = Path(self.config.get('base_directory', 'books_by_skills'))
        self.base_dir.mkdir(exist_ok=True)
        
        # Progress tracking
        self.downloaded_books: Set[str] = set()
        self.failed_books: Dict[str, str] = {}
        self.progress_lock = Lock()
        
        # Load existing progress if resuming
        if self.config.get('resume', True):
            self._load_progress()
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'base_directory': 'books_by_skills',
            'max_books_per_skill': 50,  # Limit to prevent overwhelming downloads
            'max_pages_per_skill': 5,   # Limit API pages to prevent long searches
            'download_delay': 2,        # Delay between downloads (seconds)
            'max_workers': 3,           # Concurrent download threads
            'epub_format': 'enhanced',  # 'legacy', 'enhanced', 'kindle', 'dual'
            'resume': True,             # Resume interrupted downloads
            'skills_file': 'my_favorite_skills.txt',
            'progress_file': 'download_progress.json'
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
                logging.FileHandler('skill_downloader.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('SkillDownloader')
    
    def _load_progress(self):
        """Load previous download progress"""
        progress_file = self.config['progress_file']
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    progress = json.load(f)
                self.downloaded_books = set(progress.get('downloaded', []))
                self.failed_books = progress.get('failed', {})
                self.logger.info(f"Loaded progress: {len(self.downloaded_books)} downloaded, {len(self.failed_books)} failed")
            except Exception as e:
                self.logger.warning(f"Could not load progress file: {e}")
    
    def _save_progress(self):
        """Save current download progress"""
        progress_file = self.config['progress_file']
        try:
            progress = {
                'downloaded': list(self.downloaded_books),
                'failed': self.failed_books,
                'timestamp': time.time()
            }
            with open(progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save progress: {e}")
    
    def _sanitize_skill_name(self, skill_name: str) -> str:
        """Sanitize skill name for use as directory name"""
        # Remove or replace problematic characters
        sanitized = skill_name.strip()
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            sanitized = sanitized.replace(char, '_')
        return sanitized
    
    def _get_skill_directory(self, skill_name: str) -> Path:
        """Get the directory path for a skill"""
        sanitized_name = self._sanitize_skill_name(skill_name)
        return self.base_dir / sanitized_name
    
    def load_favorite_skills(self) -> List[str]:
        """Load favorite skills from file"""
        skills_file = self.config['skills_file']
        if not os.path.exists(skills_file):
            raise FileNotFoundError(f"Skills file not found: {skills_file}")
        
        skills = []
        with open(skills_file, 'r', encoding='utf-8') as f:
            for line in f:
                skill = line.strip()
                if skill and not skill.startswith('#'):  # Skip empty lines and comments
                    skills.append(skill)
        
        self.logger.info(f"Loaded {len(skills)} favorite skills")
        return skills
    
    def search_books_for_skill(self, skill_name: str) -> List[Dict]:
        """Search for books in a specific skill"""
        self.logger.info(f"Searching for books in skill: {skill_name}")
        
        # Create skill URL (this is a pattern, may need adjustment based on O'Reilly's current structure)
        skill_url = f"https://learning.oreilly.com/search/skills/{skill_name.lower().replace(' ', '-')}/"
        
        try:
            # Use the existing parser with pagination limits
            book_ids = search_oreilly_learning_api_with_pagination(
                skill_name,
                skill_url,
                cookies=self.cookies,
                max_pages=self.config['max_pages_per_skill'],
                verbose=False  # Reduce output for automation
            )
            
            # Load detailed book info if available
            info_file = f"{skill_name.lower().replace(' ', '-')}-books-info.json"
            books_info = []
            
            if os.path.exists(info_file):
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        books_info = json.load(f)
                    self.logger.info(f"Found {len(books_info)} detailed book records for {skill_name}")
                except Exception as e:
                    self.logger.warning(f"Could not load book info for {skill_name}: {e}")
            
            # Limit the number of books
            max_books = self.config['max_books_per_skill']
            if len(book_ids) > max_books:
                self.logger.info(f"Limiting {skill_name} to {max_books} books (found {len(book_ids)})")
                book_ids = book_ids[:max_books]
                if books_info:
                    books_info = books_info[:max_books]
            
            return books_info if books_info else [{'id': bid, 'title': f'Book {bid}'} for bid in book_ids]
            
        except Exception as e:
            self.logger.error(f"Error searching books for {skill_name}: {e}")
            return []
    
    def download_single_book(self, book_info: Dict, skill_name: str, skill_dir: Path) -> bool:
        """Download a single book"""
        book_id = book_info.get('id', '')
        book_title = book_info.get('title', f'Book {book_id}')
        
        # Check if already downloaded
        with self.progress_lock:
            if book_id in self.downloaded_books:
                self.logger.info(f"⏭️  Skipping {book_title} (already downloaded)")
                return True
        
        self.logger.info(f"📚 Downloading: {book_title} (ID: {book_id})")
        
        try:
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
            
            # Change to skill directory temporarily
            original_cwd = os.getcwd()
            os.chdir(skill_dir)
            
            try:
                # Initialize and run the downloader
                downloader = OreillyBooks(args)
                
                # Mark as downloaded
                with self.progress_lock:
                    self.downloaded_books.add(book_id)
                    if book_id in self.failed_books:
                        del self.failed_books[book_id]
                
                self.logger.info(f"✅ Successfully downloaded: {book_title}")
                return True
                
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            self.logger.error(f"❌ Failed to download {book_title}: {e}")
            with self.progress_lock:
                self.failed_books[book_id] = str(e)
            return False
    
    def download_books_for_skill(self, skill_name: str) -> Dict[str, int]:
        """Download all books for a specific skill"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Processing skill: {skill_name}")
        self.logger.info(f"{'='*60}")
        
        # Create skill directory
        skill_dir = self._get_skill_directory(skill_name)
        skill_dir.mkdir(exist_ok=True)
        
        # Search for books
        books_info = self.search_books_for_skill(skill_name)
        if not books_info:
            self.logger.warning(f"No books found for skill: {skill_name}")
            return {'total': 0, 'downloaded': 0, 'failed': 0, 'skipped': 0}
        
        self.logger.info(f"Found {len(books_info)} books for {skill_name}")
        
        # Download books
        results = {'total': len(books_info), 'downloaded': 0, 'failed': 0, 'skipped': 0}
        
        if self.config['max_workers'] > 1:
            # Parallel downloads
            with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
                future_to_book = {
                    executor.submit(self.download_single_book, book_info, skill_name, skill_dir): book_info
                    for book_info in books_info
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
            for book_info in books_info:
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
        results['skipped'] = len([b for b in books_info if b.get('id', '') in self.downloaded_books]) - results['downloaded']
        
        self.logger.info(f"Completed {skill_name}: {results}")
        return results
    
    def download_all_skills(self, skill_filter: List[str] = None) -> Dict[str, Dict]:
        """Download books for all favorite skills"""
        skills = self.load_favorite_skills()
        
        if skill_filter:
            skills = [s for s in skills if any(f.lower() in s.lower() for f in skill_filter)]
            self.logger.info(f"Filtered to {len(skills)} skills matching: {skill_filter}")
        
        total_results = {
            'skills_processed': 0,
            'total_books': 0,
            'total_downloaded': 0,
            'total_failed': 0,
            'total_skipped': 0,
            'skill_results': {}
        }
        
        self.logger.info(f"Starting download for {len(skills)} skills")
        start_time = time.time()
        
        for i, skill_name in enumerate(skills, 1):
            self.logger.info(f"\nProgress: {i}/{len(skills)} skills")
            
            try:
                skill_results = self.download_books_for_skill(skill_name)
                total_results['skill_results'][skill_name] = skill_results
                total_results['skills_processed'] += 1
                total_results['total_books'] += skill_results['total']
                total_results['total_downloaded'] += skill_results['downloaded']
                total_results['total_failed'] += skill_results['failed']
                total_results['total_skipped'] += skill_results['skipped']
                
                # Save progress after each skill
                self._save_progress()
                
            except Exception as e:
                self.logger.error(f"Error processing skill {skill_name}: {e}")
                total_results['skill_results'][skill_name] = {'error': str(e)}
        
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
        
        return total_results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Automated O'Reilly Books Downloader by Skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all favorite skills
  python automate_skill_downloads.py
  
  # Download specific skills
  python automate_skill_downloads.py --skills "Python" "Machine Learning" "AI"
  
  # Use custom configuration
  python automate_skill_downloads.py --config my_config.json
  
  # Limit downloads per skill
  python automate_skill_downloads.py --max-books 20 --max-pages 3
        """
    )
    
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--skills', '-s', nargs='+', help='Specific skills to download (filters the list)')
    parser.add_argument('--max-books', type=int, help='Maximum books per skill')
    parser.add_argument('--max-pages', type=int, help='Maximum API pages per skill')
    parser.add_argument('--workers', type=int, help='Number of concurrent download threads')
    parser.add_argument('--format', choices=['legacy', 'enhanced', 'kindle', 'dual'], 
                       help='EPUB format to generate')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be downloaded without actually downloading')
    
    args = parser.parse_args()
    
    # Initialize downloader
    downloader = SkillBookDownloader(args.config)
    
    # Override config with command line arguments
    if args.max_books:
        downloader.config['max_books_per_skill'] = args.max_books
    if args.max_pages:
        downloader.config['max_pages_per_skill'] = args.max_pages
    if args.workers:
        downloader.config['max_workers'] = args.workers
    if args.format:
        downloader.config['epub_format'] = args.format
    if args.verbose:
        downloader.config['verbose'] = True
    
    if args.dry_run:
        print("DRY RUN MODE - No downloads will be performed")
        skills = downloader.load_favorite_skills()
        if args.skills:
            skills = [s for s in skills if any(f.lower() in s.lower() for f in args.skills)]
        
        print(f"Would process {len(skills)} skills:")
        for skill in skills:
            print(f"  - {skill}")
        return
    
    try:
        # Start the download process
        results = downloader.download_all_skills(args.skills)
        
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
