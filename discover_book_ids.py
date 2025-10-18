#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Book ID Discovery Script - Step 1
Discovers and saves all book IDs for each skill category
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
import requests

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from oreilly_parser.oreilly_books_parser import load_cookies


class BookIDDiscoverer:
    """Discovers and saves book IDs for all skills"""
    
    def __init__(self, config_file: str = None, update_mode: bool = False):
        self.config = self._load_config(config_file)
        self.setup_logging()
        self.update_mode = update_mode  # Whether to re-discover already discovered skills
        
        # Load authentication cookies
        self.cookies = load_cookies()
        if not self.cookies:
            self.logger.warning("No authentication cookies found. Some content may not be accessible.")
        
        # Create output directory
        self.output_dir = Path(self.config.get('book_ids_directory', 'book_ids'))
        self.output_dir.mkdir(exist_ok=True)
        
        # Progress tracking
        self.discovered_skills: Set[str] = set()
        self.failed_skills: Dict[str, str] = {}
        self.skipped_skills: Set[str] = set()  # Track skipped skills
        self.progress_lock = Lock()
        
        # Load existing progress if resuming
        if self.config.get('resume', True):
            self._load_progress()
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'book_ids_directory': 'book_ids',
            'max_pages_per_skill': 100,
            'books_per_page': 50,  # O'Reilly API returns ~50 books per page
            'max_workers': 3,
            'discovery_delay': 2,
            'resume': True,
            'skills_file': 'favorite_skills_with_counts.json',
            'progress_file': 'output/discovery_progress.json',
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
                logging.FileHandler('book_id_discovery.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('BookIDDiscoverer')
    
    def _load_progress(self):
        """Load previous discovery progress"""
        progress_file = self.config['progress_file']
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    progress = json.load(f)
                self.discovered_skills = set(progress.get('discovered', []))
                self.failed_skills = progress.get('failed', {})
                self.logger.info(f"Loaded progress: {len(self.discovered_skills)} skills discovered, {len(self.failed_skills)} failed")
            except Exception as e:
                self.logger.warning(f"Could not load progress file: {e}")
    
    def _save_progress(self):
        """Save current discovery progress"""
        progress_file = self.config['progress_file']
        try:
            progress = {
                'discovered': list(self.discovered_skills),
                'failed': self.failed_skills,
                'timestamp': time.time()
            }
            # Ensure output directory exists
            os.makedirs(os.path.dirname(progress_file), exist_ok=True)
            with open(progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save progress: {e}")
    
    def load_favorite_skills(self) -> List[Dict]:
        """Load favorite skills from JSON file with book counts"""
        skills_file = self.config['skills_file']
        if not os.path.exists(skills_file):
            raise FileNotFoundError(f"Skills file not found: {skills_file}")
        
        with open(skills_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        skills = data.get('skills', [])
        self.logger.info(f"Loaded {len(skills)} favorite skills from JSON")
        
        # Log total expected books
        total_books = sum(skill['books'] for skill in skills)
        self.logger.info(f"Total expected books across all skills: {total_books:,}")
        
        return skills
    
    def _search_oreilly_api(self, skill_name: str, page: int = 1, rows: int = 100) -> Dict:
        """Search O'Reilly v1 API for books in a specific skill/topic
        
        Args:
            skill_name: Name of the skill to search
            page: Page number for pagination (default: 1, first page)
            rows: Number of rows to return per page (default: 100)
        
        Returns:
            Dict containing search results with books list
        """
        # Build API URL - using v1 API which is simpler and works reliably
        url = "https://learning.oreilly.com/api/v1/search"
        params = {
            'q': skill_name,  # Simple query with skill name
            'rows': rows,
            'page': page
        }
        
        # Headers
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        }
        
        # Make request with cookies
        try:
            response = requests.get(url, params=params, headers=headers, cookies=self.cookies, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed for {skill_name}: {e}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response for {skill_name}: {e}")
            raise
    
    def _get_skill_variants(self, skill_name: str) -> List[str]:
        """Get variants of a skill name for matching subjects/topics
        
        Generates simple separator variants:
        - Original: "Engineering Leadership"
        - Hyphen: "Engineering-Leadership"
        - Underscore: "Engineering_Leadership"
        - Plus: "Engineering+Leadership"
        
        Args:
            skill_name: The skill name to generate variants for
            
        Returns:
            List of skill name variants (original + separator variants)
        """
        variants = [skill_name]  # Original with spaces
        skill_lower = skill_name.lower()
        
        # Add separator variants
        if ' ' in skill_lower:
            variants.append(skill_lower.replace(' ', '-'))    # Hyphen
            variants.append(skill_lower.replace(' ', '_'))    # Underscore
            variants.append(skill_lower.replace(' ', '+'))    # Plus
        
        # Remove duplicates and return
        return list(set(variants))
    
    def discover_books_for_skill(self, skill_name: str, expected_book_count: int = None) -> Dict:
        """Discover all books for a specific skill using the O'Reilly v1 API
        
        Args:
            skill_name: Name of the skill to discover
            expected_book_count: Expected number of books (from JSON), used for validation
        """
        self.logger.info(f"🔍 Discovering books for skill: {skill_name}")
        
        if expected_book_count:
            self.logger.info(f"📊 Expected book count: {expected_book_count}")
            
            # Skip if book count is greater than 500
            if expected_book_count > 500:
                self.logger.warning(f"⏭️  Skipping '{skill_name}': Book count ({expected_book_count}) exceeds 500")
                with self.progress_lock:
                    self.skipped_skills.add(skill_name)
                return {
                    'skill': skill_name,
                    'total_books': 0,
                    'expected_books': expected_book_count,
                    'book_ids': [],
                    'books_info': [],
                    'success': True,
                    'skipped': True,
                    'reason': 'Book count exceeds 500'
                }
        
        try:
            all_books = []
            book_ids_set = set()  # Use set to avoid duplicates
            page = 1
            rows_per_request = 100  # Request parameter (API may return fewer)
            results_per_page = 15  # Typical results per page from v1 API
            
            # Calculate estimated pages needed based on expected count
            if expected_book_count:
                target_book_count = expected_book_count  # No buffer
                estimated_pages = (target_book_count // results_per_page) + 2  # Add 2 pages as extra buffer
                self.logger.info(f"📖 '{skill_name}': Target {target_book_count} books (expected {expected_book_count})")
                self.logger.info(f"📖 '{skill_name}': Estimated pages needed ~{estimated_pages}")
            else:
                target_book_count = None
                estimated_pages = 100  # Default max if no expectation
            
            # Paginate through all results
            while True:
                self.logger.debug(f"Fetching page {page}")
                
                # Make API request
                response_data = self._search_oreilly_api(skill_name, page=page, rows=rows_per_request)
                
                # v1 API returns a simple list of results
                results = response_data.get('results', [])
                
                # Stop if no results found
                if not results:
                    self.logger.info(f"📄 Page {page} of '{skill_name}': No more results found, stopping pagination")
                    break
                
                # Log with target count if available
                if target_book_count:
                    self.logger.info(f"📄 Page {page} of '{skill_name}': Found {len(results)} books (Total so far: {len(all_books)} of {target_book_count} target)")
                else:
                    self.logger.info(f"📄 Page {page} of '{skill_name}': Found {len(results)} books (Total so far: {len(all_books)})")
                
                # Process each book with validation
                for book in results:
                    # === VALIDATION RULES ===
                    
                    # 1. Format validation - Only books, skip videos, courses, audiobooks
                    format_type = book.get('format', '').lower()
                    if format_type not in ['book', 'ebook', '']:
                        self.logger.debug(f"⏭️  Skipping {format_type}: {book.get('title', 'Unknown')}")
                        continue
                    
                    # 2. Language validation - English only
                    language = book.get('language', '').lower()
                    if language and language not in ['en', 'english', '']:
                        self.logger.debug(f"⏭️  Skipping non-English ({language}): {book.get('title', 'Unknown')}")
                        continue
                    
                    # 3. Title validation
                    title = book.get('title', '')
                    title_lower = title.lower()
                    
                    # Skip if title is too short (likely not a real book)
                    if len(title.strip()) < 5:
                        self.logger.debug(f"⏭️  Skipping short title: {title}")
                        continue
                    
                    # Skip chapters and non-book content (but not "parts" as they are legitimate books)
                    chapter_keywords = [
                        'chapter', 'section', 'lesson', 'unit', 'module',
                        'chapter 1:', 'chapter 2:', 'chapter 3:', 'chapter 4:', 'chapter 5:',
                        'chapter 6:', 'chapter 7:', 'chapter 8:', 'chapter 9:', 'chapter 10:',
                        'section 1:', 'section 2:', 'section 3:', 'section 4:', 'section 5:',
                        'lesson 1:', 'lesson 2:', 'lesson 3:', 'lesson 4:', 'lesson 5:',
                        'unit 1:', 'unit 2:', 'unit 3:', 'unit 4:', 'unit 5:',
                        'exam ref', 'certification', 'study guide', 'practice test',
                        'appendix', 'glossary', 'index', 'bibliography',
                        'closing thoughts', 'conclusion', 'summary', 'wrap-up',
                        'introduction', 'preface', 'foreword', 'acknowledgments'
                    ]
                    if any(keyword in title_lower for keyword in chapter_keywords):
                        self.logger.debug(f"⏭️  Skipping chapter/section: {title}")
                        continue
                    
                    # Skip if title is just a number or very short
                    if len(title.strip()) <= 5 and title.strip().isdigit():
                        self.logger.debug(f"⏭️  Skipping numeric only: {title}")
                        continue
                    
                    # Skip titles starting with numbers (likely chapters) - but be specific
                    if title.strip() and title.strip()[0].isdigit():
                        # Only skip simple numbered items like "1. Introduction"
                        if len(title.split()) <= 3 and ('.' in title or title.count(' ') <= 2):
                            self.logger.debug(f"⏭️  Skipping numbered item: {title}")
                            continue
                    
                    # 4. ISBN validation
                    isbn = book.get('isbn', '').strip()
                    has_isbn = isbn and isbn != '' and isbn.lower() not in ['n/a', 'none', 'null']
                    
                    # Get book ID
                    book_id = book.get('archive_id') or book.get('isbn') or book.get('ourn')
                    
                    # If no ISBN, check if it looks like a legitimate book
                    if not has_isbn:
                        # Skip if it's clearly a chapter, video, course, or short content
                        non_book_keywords = [
                            'chapter', 'section', 'lesson', 'unit', 'module',
                            'video', 'course', 'tutorial', 'workshop', 'webinar', 'audiobook'
                        ]
                        if any(keyword in title_lower for keyword in non_book_keywords) or len(title.strip()) < 15:
                            self.logger.debug(f"⏭️  Skipping no ISBN (likely chapter/video/course): {title}")
                            continue
                        else:
                            # It might be a legitimate book without ISBN
                            self.logger.debug(f"⚠️  Book without ISBN (keeping): {title}")
                    
                    # 5. Subject validation - must include the skill or variant
                    subjects = book.get('subjects', []) or book.get('topics', [])
                    skill_variants = self._get_skill_variants(skill_name)
                    
                    has_matching_subject = False
                    if subjects:
                        subjects_lower = [str(s).lower() for s in subjects]
                        for variant in skill_variants:
                            if any(variant.lower() in subject for subject in subjects_lower):
                                has_matching_subject = True
                                break
                    
                    if subjects and not has_matching_subject:
                        self.logger.debug(f"⏭️  Skipping - subjects don't match skill '{skill_name}': {title} (subjects: {subjects})")
                        continue
                    
                    # 6. Topics validation - must include the skill or variant
                    topics = book.get('topics', [])
                    has_matching_topic = False
                    if topics:
                        topics_lower = [str(t).lower() for t in topics]
                        for variant in skill_variants:
                            if any(variant.lower() in topic for topic in topics_lower):
                                has_matching_topic = True
                                break
                    
                    if topics and not has_matching_topic:
                        self.logger.debug(f"⏭️  Skipping - topics don't match skill '{skill_name}': {title} (topics: {topics})")
                        continue
                    
                    # 7. Duplicate check
                    if book_id and book_id not in book_ids_set:
                        book_ids_set.add(book_id)
                        
                        # Extract book info in the original format for compatibility
                        # Format matches the old parser output
                        book_info = {
                            'title': title,
                            'id': f"https://www.safaribooksonline.com/api/v1/book/{book_id}/",
                            'url': book.get('url', f"https://learning.oreilly.com/api/v1/book/{book_id}/"),
                            'isbn': isbn if has_isbn else book_id,
                            'format': book.get('format', 'book')
                        }
                        all_books.append(book_info)
                        self.logger.debug(f"✅ Added book: {title}")
                
                # Check if we've reached the target count (exact match)
                if target_book_count and len(all_books) >= target_book_count:
                    self.logger.info(f"✓ '{skill_name}': Reached target count ({len(all_books)}/{target_book_count})")
                    break
                
                # Move to next page
                page += 1
                
                # Add small delay between requests to be nice to the API
                time.sleep(0.5)
                
                # Safety check: don't paginate infinitely
                # Use the larger of estimated_pages or 200 as max
                max_pages = max(estimated_pages, 200)
                if page > max_pages:
                    self.logger.warning(f"Reached maximum pagination limit ({max_pages} pages) for {skill_name}")
                    break
            
            # Save discovered books to skill-specific file
            self._save_skill_books(skill_name, all_books)
            
            # Calculate filtering statistics
            books_with_isbn = sum(1 for book in all_books if book.get('isbn', '').strip() and 
                                  book.get('isbn', '').strip() not in ['n/a', 'none', 'null'])
            books_without_isbn = len(all_books) - books_with_isbn
            
            # Log filtering statistics
            self.logger.info(f"📊 '{skill_name}' Filtering Results:")
            self.logger.info(f"   📚 Total books found: {len(all_books)}")
            self.logger.info(f"   📖 Books with ISBN: {books_with_isbn}")
            self.logger.info(f"   📝 Books without ISBN: {books_without_isbn}")
            self.logger.info(f"   ⏭️  Filtered out: videos, chapters, courses, non-English content")
            
            result = {
                'skill': skill_name,
                'total_books': len(all_books),
                'expected_books': expected_book_count,
                'book_ids': list(book_ids_set),
                'books_info': all_books,
                'books_with_isbn': books_with_isbn,
                'books_without_isbn': books_without_isbn,
                'success': True
            }
            
            with self.progress_lock:
                self.discovered_skills.add(skill_name)
                if skill_name in self.failed_skills:
                    del self.failed_skills[skill_name]
            
            # Log comparison with expected count
            if expected_book_count:
                diff = len(all_books) - expected_book_count
                if diff == 0:
                    self.logger.info(f"✅ '{skill_name}': Discovered {len(all_books)} books (matches expected count)")
                elif diff > 0:
                    self.logger.info(f"✅ '{skill_name}': Discovered {len(all_books)} books (+{diff} more than expected)")
                else:
                    self.logger.warning(f"⚠️  '{skill_name}': Discovered {len(all_books)} books ({diff} fewer than expected {expected_book_count})")
            else:
                self.logger.info(f"✅ '{skill_name}': Discovered {len(all_books)} books")
            
            return result
            
        except Exception as e:
            error_msg = f"Error discovering books for {skill_name}: {e}"
            self.logger.error(error_msg)
            
            with self.progress_lock:
                self.failed_skills[skill_name] = str(e)
            
            return {
                'skill': skill_name,
                'total_books': 0,
                'book_ids': [],
                'books_info': [],
                'success': False,
                'error': str(e)
            }
    
    def _save_skill_books(self, skill_name: str, books_info: List[Dict]):
        """Save discovered books for a skill to JSON file"""
        sanitized_name = self._sanitize_skill_name(skill_name)
        output_file = self.output_dir / f"{sanitized_name}_books.json"
        
        try:
            skill_data = {
                'skill_name': skill_name,
                'discovery_timestamp': time.time(),
                'total_books': len(books_info),
                'books': books_info
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(skill_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 Saved {len(books_info)} books to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save books for {skill_name}: {e}")
    
    def _sanitize_skill_name(self, skill_name: str) -> str:
        """Sanitize skill name for use as filename - lowercase with underscores"""
        # Convert to lowercase and replace spaces with underscores
        sanitized = skill_name.strip().lower().replace(' ', '_')
        # Replace any other problematic characters with underscores
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '&', '-', '(', ')', '.', ',']:
            sanitized = sanitized.replace(char, '_')
        # Replace multiple consecutive underscores with single underscore
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized
    
    def _is_skill_already_discovered(self, skill_name: str) -> bool:
        """Check if a skill has already been discovered (JSON file exists)"""
        sanitized_name = self._sanitize_skill_name(skill_name)
        output_file = self.output_dir / f"{sanitized_name}_books.json"
        return output_file.exists()
    
    def discover_all_skills(self, skill_filter: List[str] = None) -> Dict:
        """Discover books for all favorite skills"""
        skills_data = self.load_favorite_skills()
        
        if skill_filter:
            skills_data = [s for s in skills_data if any(f.lower() in s['title'].lower() for f in skill_filter)]
            self.logger.info(f"Filtered to {len(skills_data)} skills matching: {skill_filter}")
        
        # Filter out excluded skills
        if self.config.get('exclude_skills'):
            skills_data = [s for s in skills_data if s['title'] not in self.config['exclude_skills']]
        
        # Filter out already discovered skills if not in update mode
        if not self.update_mode:
            original_count = len(skills_data)
            skills_data = [s for s in skills_data if not self._is_skill_already_discovered(s['title'])]
            skipped_count = original_count - len(skills_data)
            if skipped_count > 0:
                self.logger.info(f"⏭️  Skipping {skipped_count} already discovered skills (use --update to re-discover)")
                self.logger.info(f"📋 Remaining skills to discover: {len(skills_data)}")
        else:
            self.logger.info(f"🔄 Update mode: Will re-discover all skills including existing ones")
        
        # Prioritize skills if specified
        priority_skills = self.config.get('priority_skills', [])
        if priority_skills:
            priority_found = [s for s in skills_data if s['title'] in priority_skills]
            other_skills = [s for s in skills_data if s['title'] not in priority_skills]
            skills_data = priority_found + other_skills
            self.logger.info(f"Prioritized {len(priority_found)} skills")
        
        total_results = {
            'skills_processed': 0,
            'total_books_discovered': 0,
            'total_books_expected': sum(s['books'] for s in skills_data),
            'successful_skills': 0,
            'failed_skills': 0,
            'skipped_skills': 0,
            'skill_results': {}
        }
        
        self.logger.info(f"Starting discovery for {len(skills_data)} skills")
        self.logger.info(f"Total expected books: {total_results['total_books_expected']:,}")
        start_time = time.time()
        
        if self.config['max_workers'] > 1:
            # Parallel discovery
            with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
                future_to_skill = {
                    executor.submit(self.discover_books_for_skill, skill['title'], skill['books']): skill['title']
                    for skill in skills_data
                }
                
                for future in as_completed(future_to_skill):
                    skill_name = future_to_skill[future]
                    try:
                        result = future.result()
                        total_results['skill_results'][skill_name] = result
                        total_results['skills_processed'] += 1
                        
                        if result.get('skipped', False):
                            total_results['skipped_skills'] += 1
                        elif result['success']:
                            total_results['successful_skills'] += 1
                            total_results['total_books_discovered'] += result['total_books']
                        else:
                            total_results['failed_skills'] += 1
                            
                    except Exception as e:
                        self.logger.error(f"Exception processing skill {skill_name}: {e}")
                        total_results['skill_results'][skill_name] = {
                            'skill': skill_name,
                            'success': False,
                            'error': str(e)
                        }
                        total_results['failed_skills'] += 1
                    
                    # Save progress periodically
                    self._save_progress()
                    
                    # Add delay between discoveries
                    time.sleep(self.config['discovery_delay'])
        else:
            # Sequential discovery
            for skill_data in skills_data:
                skill_name = skill_data['title']
                expected_books = skill_data['books']
                result = self.discover_books_for_skill(skill_name, expected_books)
                total_results['skill_results'][skill_name] = result
                total_results['skills_processed'] += 1
                
                if result.get('skipped', False):
                    total_results['skipped_skills'] += 1
                elif result['success']:
                    total_results['successful_skills'] += 1
                    total_results['total_books_discovered'] += result['total_books']
                else:
                    total_results['failed_skills'] += 1
                
                # Save progress
                self._save_progress()
                
                # Add delay between discoveries
                time.sleep(self.config['discovery_delay'])
        
        # Final summary
        elapsed_time = time.time() - start_time
        self.logger.info(f"\n{'='*60}")
        self.logger.info("DISCOVERY SUMMARY")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Skills processed: {total_results['skills_processed']}")
        self.logger.info(f"Successful skills: {total_results['successful_skills']}")
        self.logger.info(f"Failed skills: {total_results['failed_skills']}")
        self.logger.info(f"Skipped skills (>500 books): {total_results['skipped_skills']}")
        if len(self.skipped_skills) > 0:
            self.logger.info(f"  Skipped skill list: {', '.join(sorted(self.skipped_skills))}")
        self.logger.info(f"Total books discovered: {total_results['total_books_discovered']:,}")
        self.logger.info(f"Total books expected: {total_results['total_books_expected']:,}")
        diff = total_results['total_books_discovered'] - total_results['total_books_expected']
        self.logger.info(f"Difference: {diff:+,} books")
        self.logger.info(f"Total time: {elapsed_time/3600:.1f} hours")
        
        # Save final results
        results_file = 'discovery_results.json'
        with open(results_file, 'w') as f:
            json.dump(total_results, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Detailed results saved to: {results_file}")
        
        # Create summary file
        self._create_summary_file(total_results)
        
        return total_results
    
    def _create_summary_file(self, results: Dict):
        """Create a human-readable summary file"""
        summary_file = 'discovery_summary.txt'
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("O'REILLY BOOKS DISCOVERY SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total Skills Processed: {results['skills_processed']}\n")
            f.write(f"Successful Skills: {results['successful_skills']}\n")
            f.write(f"Failed Skills: {results['failed_skills']}\n")
            f.write(f"Skipped Skills (>500 books): {results.get('skipped_skills', 0)}\n")
            f.write(f"Total Books Discovered: {results['total_books_discovered']:,}\n")
            f.write(f"Total Books Expected: {results.get('total_books_expected', 0):,}\n")
            diff = results['total_books_discovered'] - results.get('total_books_expected', 0)
            f.write(f"Difference: {diff:+,} books\n\n")
            
            f.write("TOP SKILLS BY BOOK COUNT:\n")
            f.write("-" * 30 + "\n")
            
            # Sort skills by book count
            skill_counts = []
            for skill_name, result in results['skill_results'].items():
                if result['success']:
                    skill_counts.append((skill_name, result['total_books']))
            
            skill_counts.sort(key=lambda x: x[1], reverse=True)
            
            for skill_name, count in skill_counts[:20]:  # Top 20
                f.write(f"{skill_name}: {count:,} books\n")
            
            if len(skill_counts) > 20:
                f.write(f"... and {len(skill_counts) - 20} more skills\n")
            
            f.write(f"\nDetailed results available in: discovery_results.json\n")
            f.write(f"Individual skill files in: {self.output_dir}/\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Discover Book IDs for O'Reilly Skills - Step 1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover all favorite skills
  python3 discover_book_ids.py
  
  # Discover specific skills
  python3 discover_book_ids.py --skills "Python" "Machine Learning" "AI"
  
  # Use custom configuration
  python3 discover_book_ids.py --config my_config.json
  
  # High performance discovery
  python3 discover_book_ids.py --workers 5 --max-pages 50
        """
    )
    
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--skills', '-s', nargs='+', help='Specific skills to discover (filters the list)')
    parser.add_argument('--max-pages', type=int, help='Maximum API pages per skill')
    parser.add_argument('--workers', type=int, help='Number of concurrent discovery threads')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--update', '-u', action='store_true', help='Re-discover already discovered skills (update existing files)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be discovered without actually discovering')
    
    args = parser.parse_args()
    
    # Initialize discoverer
    discoverer = BookIDDiscoverer(args.config, update_mode=args.update)
    
    # Override config with command line arguments
    if args.max_pages:
        discoverer.config['max_pages_per_skill'] = args.max_pages
    if args.workers:
        discoverer.config['max_workers'] = args.workers
    if args.verbose:
        discoverer.config['verbose'] = True
    
    if args.dry_run:
        print("DRY RUN MODE - No discovery will be performed")
        skills_data = discoverer.load_favorite_skills()
        if args.skills:
            skills_data = [s for s in skills_data if any(f.lower() in s['title'].lower() for f in args.skills)]
        
        print(f"Would discover books for {len(skills_data)} skills:")
        total_expected = 0
        for skill_data in skills_data:
            print(f"  - {skill_data['title']} ({skill_data['books']} books)")
            total_expected += skill_data['books']
        print(f"\nTotal expected books: {total_expected:,}")
        return
    
    try:
        # Start the discovery process
        results = discoverer.discover_all_skills(args.skills)
        
        # Print final summary
        print(f"\n🎉 Discovery completed!")
        print(f"📚 Discovered {results['total_books_discovered']:,} books")
        print(f"📁 Organized in {results['successful_skills']} skill files")
        print(f"📊 Check 'discovery_summary.txt' for detailed breakdown")
        
    except KeyboardInterrupt:
        print("\n⚠️  Discovery interrupted by user")
        print("💾 Progress saved - you can resume later by running the script again")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
