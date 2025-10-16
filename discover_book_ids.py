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

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from oreilly_parser.oreilly_books_parser import search_oreilly_learning_api_with_pagination, load_cookies


class BookIDDiscoverer:
    """Discovers and saves book IDs for all skills"""
    
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        self.setup_logging()
        
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
        self.progress_lock = Lock()
        
        # Load existing progress if resuming
        if self.config.get('resume', True):
            self._load_progress()
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'book_ids_directory': 'book_ids',
            'max_pages_per_skill': 100,
            'max_workers': 3,
            'discovery_delay': 2,
            'resume': True,
            'skills_file': 'my_favorite_skills.txt',
            'progress_file': 'discovery_progress.json',
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
            with open(progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save progress: {e}")
    
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
    
    def discover_books_for_skill(self, skill_name: str) -> Dict:
        """Discover all books for a specific skill"""
        self.logger.info(f"🔍 Discovering books for skill: {skill_name}")
        
        # Create skill URL
        skill_url = f"https://learning.oreilly.com/search/skills/{skill_name.lower().replace(' ', '-')}/"
        
        try:
            # Set temp directory for parser
            temp_dir = Path(self.config.get('temp_directory', 'temp_discovery'))
            temp_dir.mkdir(exist_ok=True)
            
            # Change to temp directory temporarily for parser
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Use the existing parser with pagination
                book_ids = search_oreilly_learning_api_with_pagination(
                    skill_name,
                    skill_url,
                    cookies=self.cookies,
                    max_pages=self.config['max_pages_per_skill'],
                    verbose=False
                )
            finally:
                os.chdir(original_cwd)
            
            # Load detailed book info if available (from temp folder)
            temp_dir = Path(self.config.get('temp_directory', 'temp_discovery'))
            temp_dir.mkdir(exist_ok=True)
            info_file = temp_dir / f"{skill_name.lower().replace(' ', '-')}-books-info.json"
            books_info = []
            
            if info_file.exists():
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        books_info = json.load(f)
                    self.logger.info(f"📚 Found {len(books_info)} detailed book records for {skill_name}")
                except Exception as e:
                    self.logger.warning(f"Could not load book info for {skill_name}: {e}")
            
            # If no detailed info, create basic info from book IDs
            if not books_info and book_ids:
                books_info = [{'id': bid, 'title': f'Book {bid}', 'skill': skill_name} for bid in book_ids]
            
            # Save discovered books to skill-specific file
            self._save_skill_books(skill_name, books_info)
            
            result = {
                'skill': skill_name,
                'total_books': len(books_info),
                'book_ids': book_ids,
                'books_info': books_info,
                'success': True
            }
            
            with self.progress_lock:
                self.discovered_skills.add(skill_name)
                if skill_name in self.failed_skills:
                    del self.failed_skills[skill_name]
            
            self.logger.info(f"✅ Discovered {len(books_info)} books for {skill_name}")
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
        """Sanitize skill name for use as filename"""
        sanitized = skill_name.strip()
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '&']:
            sanitized = sanitized.replace(char, '_')
        return sanitized
    
    def discover_all_skills(self, skill_filter: List[str] = None) -> Dict:
        """Discover books for all favorite skills"""
        skills = self.load_favorite_skills()
        
        if skill_filter:
            skills = [s for s in skills if any(f.lower() in s.lower() for f in skill_filter)]
            self.logger.info(f"Filtered to {len(skills)} skills matching: {skill_filter}")
        
        # Filter out excluded skills
        if self.config.get('exclude_skills'):
            skills = [s for s in skills if s not in self.config['exclude_skills']]
        
        # Prioritize skills if specified
        priority_skills = self.config.get('priority_skills', [])
        if priority_skills:
            priority_found = [s for s in skills if s in priority_skills]
            other_skills = [s for s in skills if s not in priority_skills]
            skills = priority_found + other_skills
            self.logger.info(f"Prioritized {len(priority_found)} skills")
        
        total_results = {
            'skills_processed': 0,
            'total_books_discovered': 0,
            'successful_skills': 0,
            'failed_skills': 0,
            'skill_results': {}
        }
        
        self.logger.info(f"Starting discovery for {len(skills)} skills")
        start_time = time.time()
        
        if self.config['max_workers'] > 1:
            # Parallel discovery
            with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
                future_to_skill = {
                    executor.submit(self.discover_books_for_skill, skill_name): skill_name
                    for skill_name in skills
                }
                
                for future in as_completed(future_to_skill):
                    skill_name = future_to_skill[future]
                    try:
                        result = future.result()
                        total_results['skill_results'][skill_name] = result
                        total_results['skills_processed'] += 1
                        
                        if result['success']:
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
            for skill_name in skills:
                result = self.discover_books_for_skill(skill_name)
                total_results['skill_results'][skill_name] = result
                total_results['skills_processed'] += 1
                
                if result['success']:
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
        self.logger.info(f"Total books discovered: {total_results['total_books_discovered']:,}")
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
            f.write(f"Total Books Discovered: {results['total_books_discovered']:,}\n\n")
            
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
    parser.add_argument('--dry-run', action='store_true', help='Show what would be discovered without actually discovering')
    
    args = parser.parse_args()
    
    # Initialize discoverer
    discoverer = BookIDDiscoverer(args.config)
    
    # Override config with command line arguments
    if args.max_pages:
        discoverer.config['max_pages_per_skill'] = args.max_pages
    if args.workers:
        discoverer.config['max_workers'] = args.workers
    if args.verbose:
        discoverer.config['verbose'] = True
    
    if args.dry_run:
        print("DRY RUN MODE - No discovery will be performed")
        skills = discoverer.load_favorite_skills()
        if args.skills:
            skills = [s for s in skills if any(f.lower() in s.lower() for f in args.skills)]
        
        print(f"Would discover books for {len(skills)} skills:")
        for skill in skills:
            print(f"  - {skill}")
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
