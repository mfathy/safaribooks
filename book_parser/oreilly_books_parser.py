#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced O'Reilly Books Parser
Fetches all book topics and extracts book IDs from each topic

@author: Enhanced by SafariBooks Team
@original: Raleigh Littles
"""

import os
import sys
import json
import csv
import re
import time
import argparse
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs
from lxml import html, etree
from typing import List, Dict, Set, Optional, Tuple, Any

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("⚠️  tqdm not available. Install with: pip install tqdm")

# Import our modular components
from auth import AuthManager
from display import Display
from config import SAFARI_BASE_URL, HEADERS


class OReillyBooksParser:
    """Enhanced O'Reilly Books Parser with topic discovery and book ID extraction"""
    
    def __init__(self, use_auth=True, output_dir="book_lists"):
        self.use_auth = use_auth
        self.output_dir = output_dir
        self.session = None
        self.display = Display("oreilly_parser.log", os.path.dirname(os.path.realpath(__file__)))
        self.cache_file = os.path.join(output_dir, "topic_cache.json")
        self.cache_data = self._load_cache()
        
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
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load topic cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.display.error(f"Failed to load cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save topic cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self.display.error(f"Failed to save cache: {e}")
    
    def _is_topic_fresh(self, topic_slug: str, max_age_days: int = 30) -> bool:
        """Check if topic data is fresh (updated within max_age_days)"""
        if topic_slug not in self.cache_data:
            return False
        
        last_updated = self.cache_data[topic_slug].get('last_updated')
        if not last_updated:
            return False
        
        try:
            last_update_date = datetime.fromisoformat(last_updated)
            age = datetime.now() - last_update_date
            return age.days < max_age_days
        except (ValueError, TypeError):
            return False
    
    def _update_topic_cache(self, topic_slug: str, book_count: int):
        """Update cache with topic information"""
        self.cache_data[topic_slug] = {
            'last_updated': datetime.now().isoformat(),
            'book_count': book_count,
            'status': 'completed'
        }
        self._save_cache()
    
    def _load_existing_topic_books(self, topic_slug: str) -> List[Dict[str, str]]:
        """Load existing books for a topic from saved files"""
        topic_file = os.path.join(self.output_dir, f"{topic_slug}.json")
        if os.path.exists(topic_file):
            try:
                with open(topic_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('books', [])
            except (json.JSONDecodeError, IOError):
                pass
        return []
    
    def discover_topics(self, force_refresh: bool = False) -> List[Dict[str, str]]:
        """Discover all available topics/categories from O'Reilly Learning with caching"""
        topics_cache_file = os.path.join(self.output_dir, "topics_cache.json")
        
        # Check if we have cached topics and they're fresh (less than 7 days old)
        if not force_refresh and os.path.exists(topics_cache_file):
            try:
                cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(topics_cache_file))
                if cache_age.days < 7:
                    self.display.info("📁 Loading topics from cache...")
                    with open(topics_cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                        topics = cached_data.get('topics', [])
                        self.display.info(f"✅ Loaded {len(topics)} topics from cache (age: {cache_age.days} days)")
                        return topics
            except Exception as e:
                self.display.error(f"Failed to load topics cache: {e}")
        
        self.display.info("🔍 Discovering topics from O'Reilly Learning...")
        topics = []
        
        try:
            # Method 1: Try to fetch from the topics API endpoint
            topics_api_url = f"{SAFARI_BASE_URL}/api/v1/topics/"
            self.display.info(f"📡 Fetching from API: {topics_api_url}")
            
            response = self.session.get(topics_api_url)
            if response.status_code == 200:
                try:
                    api_data = response.json()
                    if isinstance(api_data, list):
                        for topic in api_data:
                            if isinstance(topic, dict) and 'slug' in topic:
                                topics.append({
                                    'slug': topic['slug'],
                                    'title': topic.get('title', topic['slug'].replace('-', ' ').title()),
                                    'url': f"{SAFARI_BASE_URL}/search/topics/{topic['slug']}"
                                })
                    self.display.info(f"✅ Found {len(topics)} topics from API")
                except json.JSONDecodeError:
                    self.display.info("❌ API response not JSON, trying HTML parsing...")
            
            # Method 2: If API fails, try HTML parsing
            if not topics:
                self.display.info("🌐 Trying HTML parsing from topics page...")
                topics_url = f"{SAFARI_BASE_URL}/topics/"
                response = self.session.get(topics_url)
                
                if response.status_code == 200:
                    tree = html.fromstring(response.content)
                    
                    # Look for topic links in various possible locations
                    topic_selectors = [
                        '//a[contains(@href, "/search/topics/")]',
                        '//a[contains(@href, "/topics/")]',
                        '//div[contains(@class, "topic")]//a',
                        '//li[contains(@class, "topic")]//a'
                    ]
                    
                    found_topics = set()
                    
                    for selector in topic_selectors:
                        links = tree.xpath(selector)
                        for link in links:
                            href = link.get('href', '')
                            title = link.text_content().strip() if link.text_content() else ''
                            
                            if href and '/topics/' in href:
                                # Extract topic slug from URL
                                topic_slug = href.split('/topics/')[-1].split('?')[0].split('/')[0]
                                if topic_slug and topic_slug not in found_topics:
                                    found_topics.add(topic_slug)
                                    topics.append({
                                        'slug': topic_slug,
                                        'title': title or topic_slug.replace('-', ' ').title(),
                                        'url': urljoin(SAFARI_BASE_URL, href)
                                    })
                    
                    self.display.info(f"✅ Found {len(topics)} topics from HTML parsing")
            
            # Method 3: If both methods fail, use predefined list
            if not topics:
                self.display.info("📋 Using predefined topic list as fallback...")
                topics = self._get_predefined_topics()
            
            # Cache the discovered topics
            if topics:
                self._cache_topics(topics, topics_cache_file)
                self.display.info(f"💾 Cached {len(topics)} topics to {topics_cache_file}")
            
            return topics
            
        except Exception as e:
            self.display.error(f"❌ Error discovering topics: {e}")
            # Return predefined topics as fallback
            return self._get_predefined_topics()
    
    def _get_predefined_topics(self) -> List[Dict[str, str]]:
        """Get predefined topic list as fallback"""
        return [
            {"slug": "programming-languages", "title": "Programming Languages", "url": f"{SAFARI_BASE_URL}/search/topics/programming-languages"},
            {"slug": "data-science", "title": "Data Science", "url": f"{SAFARI_BASE_URL}/search/topics/data-science"},
            {"slug": "web-mobile", "title": "Web & Mobile", "url": f"{SAFARI_BASE_URL}/search/topics/web-mobile"},
            {"slug": "software-development", "title": "Software Development", "url": f"{SAFARI_BASE_URL}/search/topics/software-development"},
            {"slug": "business", "title": "Business", "url": f"{SAFARI_BASE_URL}/search/topics/business"},
            {"slug": "security", "title": "Security", "url": f"{SAFARI_BASE_URL}/search/topics/security"},
            {"slug": "cloud-computing", "title": "Cloud Computing", "url": f"{SAFARI_BASE_URL}/search/topics/cloud-computing"},
            {"slug": "artificial-intelligence", "title": "Artificial Intelligence", "url": f"{SAFARI_BASE_URL}/search/topics/artificial-intelligence"},
            {"slug": "career-development", "title": "Career Development", "url": f"{SAFARI_BASE_URL}/search/topics/career-development"},
            {"slug": "devops", "title": "DevOps", "url": f"{SAFARI_BASE_URL}/search/topics/devops"},
            {"slug": "amazon-s3", "title": "Amazon S3", "url": f"{SAFARI_BASE_URL}/search/topics/amazon-s3"},
            {"slug": "aws", "title": "Amazon Web Services", "url": f"{SAFARI_BASE_URL}/search/topics/aws"},
            {"slug": "azure", "title": "Microsoft Azure", "url": f"{SAFARI_BASE_URL}/search/topics/azure"},
            {"slug": "google-cloud", "title": "Google Cloud", "url": f"{SAFARI_BASE_URL}/search/topics/google-cloud"},
            {"slug": "docker", "title": "Docker", "url": f"{SAFARI_BASE_URL}/search/topics/docker"},
            {"slug": "kubernetes", "title": "Kubernetes", "url": f"{SAFARI_BASE_URL}/search/topics/kubernetes"},
            {"slug": "machine-learning", "title": "Machine Learning", "url": f"{SAFARI_BASE_URL}/search/topics/machine-learning"},
            {"slug": "python", "title": "Python", "url": f"{SAFARI_BASE_URL}/search/topics/python"},
            {"slug": "javascript", "title": "JavaScript", "url": f"{SAFARI_BASE_URL}/search/topics/javascript"},
            {"slug": "java", "title": "Java", "url": f"{SAFARI_BASE_URL}/search/topics/java"}
        ]
    
    def _cache_topics(self, topics: List[Dict[str, str]], cache_file: str):
        """Cache topics to JSON file"""
        try:
            cache_data = {
                'topics': topics,
                'cached_at': datetime.now().isoformat(),
                'count': len(topics)
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.display.error(f"Failed to cache topics: {e}")
    
    def extract_book_ids_from_page(self, page_content: str) -> Set[str]:
        """Extract book IDs from a single page"""
        book_ids = set()
        
        # Multiple regex patterns to catch different URL formats
        patterns = [
            r'/library/view/[^/]+/(\d{10,13})/',  # Standard library view URLs
            r'/library/cover/(\d{10,13})',        # Cover image URLs
            r'/api/v1/book/(\d{10,13})/',         # API URLs
            r'book/(\d{10,13})/',                 # Generic book URLs
            r'isbn[=:](\d{10,13})',               # ISBN patterns
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_content)
            book_ids.update(matches)
        
        return book_ids

    def get_books_for_topic(self, topic: Dict[str, str], max_pages: int = 1000) -> List[Dict[str, str]]:
        """Get all book IDs for a specific topic using multiple search strategies"""
        topic_slug = topic['slug']
        
        self.display.info(f"Fetching books for topic: {topic['title']} ({topic_slug})")
        
        all_books = []
        seen_book_ids = set()
        
        # Strategy 1: Direct topic search
        self.display.info(f"  Strategy 1: Direct topic search")
        topic_books = self._fetch_books_from_api(topic_slug, max_pages, search_type="topic")
        
        if TQDM_AVAILABLE:
            tqdm.write(f"    Found {len(topic_books)} books from direct topic search")
        for book in topic_books:
            if book['id'] not in seen_book_ids:
                seen_book_ids.add(book['id'])
                all_books.append(book)
        
        # Strategy 2: Search with common programming terms
        if topic_slug == "programming-languages":
            programming_terms = ["python", "javascript", "java", "c++", "c#", "go", "rust", "swift", "kotlin", "php", "ruby", "scala", "clojure", "haskell", "erlang", "elixir", "dart", "typescript", "r", "matlab", "perl", "lua", "assembly", "fortran", "cobol", "pascal", "ada", "prolog", "lisp", "scheme", "smalltalk", "objective-c", "visual basic", "powershell", "bash", "shell", "sql", "html", "css", "xml", "json", "yaml", "markdown"]
            
            self.display.info(f"  Strategy 2: Search with programming terms")
            for i, term in enumerate(programming_terms[:10], 1):  # Limit to first 10 terms to avoid too many requests
                self.display.info(f"    🔍 Searching for: {term} ({i}/10)")
                term_books = self._fetch_books_from_api(term, 50, search_type="query", topic_filter=topic_slug)
                new_books = 0
                for book in term_books:
                    if book['id'] not in seen_book_ids:
                        seen_book_ids.add(book['id'])
                        all_books.append(book)
                        new_books += 1
                self.display.info(f"    ✅ Found {len(term_books)} books, {new_books} new")
                time.sleep(0.3)  # Rate limiting between terms
        
        # Strategy 3: Search with topic variations
        topic_variations = {
            "programming-languages": ["programming", "coding", "development", "software engineering"],
            "data-science": ["data analysis", "machine learning", "statistics", "analytics"],
            "web-mobile": ["web development", "mobile development", "frontend", "backend"],
            "software-development": ["software engineering", "development", "programming", "coding"],
            "business": ["management", "strategy", "leadership", "entrepreneurship"],
            "security": ["cybersecurity", "information security", "network security", "penetration testing"],
            "cloud-computing": ["cloud", "aws", "azure", "google cloud", "devops"],
            "artificial-intelligence": ["ai", "machine learning", "deep learning", "neural networks"],
            "devops": ["devops", "deployment", "automation", "infrastructure"],
            "career-development": ["career", "professional development", "skills", "training"]
        }
        
        if topic_slug in topic_variations:
            self.display.info(f"  Strategy 3: Search with topic variations")
            variations = topic_variations[topic_slug][:5]  # Limit to first 5 variations
            for i, variation in enumerate(variations, 1):
                self.display.info(f"    🔍 Searching for: {variation} ({i}/{len(variations)})")
                variation_books = self._fetch_books_from_api(variation, 30, search_type="query", topic_filter=topic_slug)
                new_books = 0
                for book in variation_books:
                    if book['id'] not in seen_book_ids:
                        seen_book_ids.add(book['id'])
                        all_books.append(book)
                        new_books += 1
                self.display.info(f"    ✅ Found {len(variation_books)} books, {new_books} new")
                time.sleep(0.3)  # Rate limiting between variations
        
        self.display.info(f"Total unique books found for {topic['title']}: {len(all_books)}")
        return all_books
    
    def _fetch_books_from_api(self, search_term: str, max_pages: int, search_type: str = "topic", topic_filter: str = None) -> List[Dict[str, str]]:
        """Fetch books from API v2 with limit=100 for better performance"""
        books = []
        page = 1
        
        self.display.info(f"    📡 Starting API fetch for '{search_term}' (max {max_pages} pages)")
        
        while page <= max_pages:
            try:
                # Build API v2 URL with limit=100 for better performance
                if search_type == "topic":
                    api_url = f"{SAFARI_BASE_URL}/api/v2/search/?topic={search_term}&page={page}&limit=100"
                else:  # query search
                    api_url = f"{SAFARI_BASE_URL}/api/v2/search/?q={search_term}&page={page}&limit=100"
                    if topic_filter:
                        api_url += f"&topic={topic_filter}"
                
                self.display.info(f"    🔄 Fetching page {page}/{max_pages}...")
                self.display.info(f"    🌐 URL: {api_url}")
                
                response = self.session.get(api_url)
                self.display.info(f"    📊 Response status: {response.status_code}")
                
                if response.status_code != 200:
                    if page == 1:
                        self.display.error(f"Failed to fetch API v2: {response.status_code}")
                    else:
                        self.display.info(f"    ⏹️  No more pages available (status {response.status_code})")
                    break
                
                # Parse JSON response
                self.display.info(f"    📝 Parsing JSON response...")
                data = response.json()
                
                # Handle different response formats
                if isinstance(data, list):
                    results = data
                else:
                    results = data.get('results', [])
                
                self.display.info(f"    📚 Found {len(results)} results on page {page}")
                
                if not results:
                    self.display.info(f"    ⏹️  No more results, stopping at page {page}")
                    break
                
                # Extract book information from API response
                self.display.info(f"    🔍 Processing {len(results)} books...")
                processed_books = 0
                
                for book in results:
                    # Handle both dict and string responses
                    if isinstance(book, str):
                        # If book is a string, it might be a URL or ID
                        book_id = book.split('/')[-1] if '/' in book else book
                        books.append({
                            'id': book_id,
                            'topic': topic_filter or search_term,
                            'topic_title': search_term,
                            'title': 'Unknown Title',
                            'authors': '',
                            'isbn': book_id,
                            'issued': '',
                            'url': f"{SAFARI_BASE_URL}/library/view/book/{book_id}/"
                        })
                    elif isinstance(book, dict):
                        book_id = book.get('archive_id') or book.get('isbn') or book.get('id')
                        if book_id:
                            # Clean up book_id if it's a URL
                            if '/' in str(book_id):
                                book_id = str(book_id).split('/')[-1]
                            
                            # Handle authors field safely
                            authors_list = book.get('authors', [])
                            if isinstance(authors_list, list):
                                authors = ', '.join([author.get('name', '') if isinstance(author, dict) else str(author) for author in authors_list])
                            else:
                                authors = str(authors_list) if authors_list else ''
                            
                            books.append({
                                'id': book_id,
                                'topic': topic_filter or search_term,
                                'topic_title': search_term,
                                'title': book.get('title', 'Unknown Title'),
                                'authors': authors,
                                'isbn': book.get('isbn', book_id),
                                'issued': book.get('issued', ''),
                                'url': f"{SAFARI_BASE_URL}/library/view/book/{book_id}/"
                            })
                            processed_books += 1
                
                self.display.info(f"    ✅ Processed {processed_books} books from page {page}")
                self.display.info(f"    📈 Total books so far: {len(books)}")
                
                # Rate limiting (reduced since we get 100 results per page)
                self.display.info(f"    ⏱️  Waiting 0.05s before next page...")
                time.sleep(0.05)  # Reduced from 0.1 to 0.05 for better performance
                page += 1
                
            except Exception as e:
                self.display.error(f"❌ Error fetching page {page} for search '{search_term}': {e}")
                break
        
        self.display.info(f"    🎯 Completed API fetch: {len(books)} total books found")
        return books
    
    def save_results(self, all_books: List[Dict[str, str]], topics: List[Dict[str, str]], 
                    output_format: str = 'json'):
        """Save results in specified format"""
        
        if output_format == 'json':
            # Save complete data as JSON
            output_data = {
                'topics': topics,
                'books': all_books,
                'summary': {
                    'total_topics': len(topics),
                    'total_books': len(all_books),
                    'books_per_topic': {topic['slug']: len([b for b in all_books if b['topic'] == topic['slug']]) 
                                      for topic in topics}
                }
            }
            
            json_file = os.path.join(self.output_dir, 'oreilly_books_complete.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.display.info(f"Complete data saved to: {json_file}")
        
        elif output_format == 'csv':
            # Save books as CSV
            csv_file = os.path.join(self.output_dir, 'oreilly_books.csv')
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'topic', 'topic_title', 'title', 'authors', 'isbn', 'issued', 'url'])
                writer.writeheader()
                writer.writerows(all_books)
            
            self.display.info(f"Books data saved to: {csv_file}")
        
        # Always save individual topic files
        for topic in topics:
            topic_books = [book for book in all_books if book['topic'] == topic['slug']]
            
            # Save as TXT (book IDs only)
            txt_file = os.path.join(self.output_dir, f"{topic['slug']}.txt")
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join([book['id'] for book in topic_books]))
            
            # Save as JSON (with metadata)
            json_file = os.path.join(self.output_dir, f"{topic['slug']}.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'topic': topic,
                    'books': topic_books,
                    'count': len(topic_books)
                }, f, indent=2, ensure_ascii=False)
        
        # Save summary
        summary_file = os.path.join(self.output_dir, 'summary.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("O'Reilly Books Parser Results\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Total Topics: {len(topics)}\n")
            f.write(f"Total Books: {len(all_books)}\n\n")
            f.write("Books per Topic:\n")
            f.write("-" * 20 + "\n")
            
            for topic in topics:
                topic_count = len([b for b in all_books if b['topic'] == topic['slug']])
                f.write(f"{topic['title']}: {topic_count} books\n")
        
        self.display.info(f"Summary saved to: {summary_file}")
    
    def parse_all_books(self, max_pages_per_topic: int = 1000, 
                       output_format: str = 'json', force_update: bool = False, 
                       cache_days: int = 30, refresh_topics: bool = False) -> Dict[str, any]:
        """Main method to parse all books from all topics"""
        
        self.display.info("Starting O'Reilly Books Parser...")
        self.display.info(f"Output directory: {self.output_dir}")
        self.display.info(f"Max pages per topic: {max_pages_per_topic}")
        
        # Discover topics
        topics = self.discover_topics(force_refresh=refresh_topics)
        if not topics:
            self.display.error("No topics discovered. Exiting.")
            return {}
        
        # Fetch books for each topic with progress indication and smart caching
        all_books = []
        skipped_topics = []
        updated_topics = []
        
        # Create progress bar if tqdm is available
        if TQDM_AVAILABLE:
            topic_progress = tqdm(topics, desc="Processing topics", unit="topic")
        else:
            topic_progress = topics
        
        for i, topic in enumerate(topic_progress, 1):
            topic_slug = topic['slug']
            topic_title = topic['title']
            
            # Check if topic is fresh (updated within specified days)
            if not force_update and self._is_topic_fresh(topic_slug, max_age_days=cache_days):
                self.display.info(f"⏭️  Skipping {topic_title} (updated within last month)")
                skipped_topics.append(topic_title)
                
                # Load existing books for this topic from cache
                existing_books = self._load_existing_topic_books(topic_slug)
                if existing_books:
                    all_books.extend(existing_books)
                continue
            
            self.display.info(f"🔄 Processing topic {i}/{len(topics)}: {topic_title}")
            
            try:
                topic_books = self.get_books_for_topic(topic, max_pages_per_topic)
                all_books.extend(topic_books)
                updated_topics.append(topic_title)
                
                # Update cache with topic information
                self._update_topic_cache(topic_slug, len(topic_books))
                
                # Save results after each topic for immediate access
                self.display.info(f"💾 Saving results for {topic_title}...")
                self.save_results(all_books, topics[:i], output_format)
                
            except Exception as e:
                self.display.error(f"❌ Error processing topic {topic_slug}: {e}")
                continue
        
        # Save final results
        self.save_results(all_books, topics, output_format)
        
        # Display final summary
        self.display.info("=" * 50)
        self.display.info("PARSING COMPLETE")
        self.display.info("=" * 50)
        self.display.info(f"Total Topics: {len(topics)}")
        self.display.info(f"Updated Topics: {len(updated_topics)}")
        self.display.info(f"Skipped Topics (cached): {len(skipped_topics)}")
        self.display.info(f"Total Books Found: {len(all_books)}")
        self.display.info(f"Output Directory: {self.output_dir}")
        
        if skipped_topics:
            self.display.info(f"Skipped topics: {', '.join(skipped_topics)}")
        
        return {
            'topics': topics,
            'books': all_books,
            'total_topics': len(topics),
            'total_books': len(all_books),
            'updated_topics': updated_topics,
            'skipped_topics': skipped_topics
        }


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Enhanced O'Reilly Books Parser - Fetch all book topics and IDs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 oreilly_books_parser.py                    # Parse all topics (uses API v2 with 100 books/page)
  python3 oreilly_books_parser.py --no-auth          # Parse without authentication
  python3 oreilly_books_parser.py --max-pages 50     # Limit to 50 pages per topic (5000 books max)
  python3 oreilly_books_parser.py --format csv       # Output as CSV format
  python3 oreilly_books_parser.py --output my_books  # Custom output directory
  python3 oreilly_books_parser.py --topics programming-languages  # Parse specific topics only
  python3 oreilly_books_parser.py --force-update     # Force update all topics, ignoring cache
  python3 oreilly_books_parser.py --cache-days 7     # Consider cache fresh for 7 days (default: 30)
  python3 oreilly_books_parser.py --refresh-topics   # Force refresh topics cache

Features:
  - API v2 with limit=100 for 6.7x faster processing (100 books/page vs 15 books/page)
  - Smart caching: skips topics updated within last 30 days (configurable)
  - Progress indication with tqdm (install with: pip install tqdm)
  - Performance optimizations for faster parsing
        """
    )
    
    parser.add_argument(
        '--no-auth', dest='use_auth', action='store_false',
        help='Run without authentication (may have limited access)'
    )
    parser.add_argument(
        '--max-pages', type=int, default=1000,
        help='Maximum pages to fetch per topic (default: 1000)'
    )
    parser.add_argument(
        '--format', choices=['json', 'csv', 'txt'], default='json',
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--output', default='book_lists',
        help='Output directory (default: book_lists)'
    )
    parser.add_argument(
        '--topics', nargs='+',
        help='Specific topics to parse (e.g., programming-languages software-development)'
    )
    
    parser.add_argument(
        '--force-update', action='store_true',
        help='Force update all topics, ignoring cache (default: False)'
    )
    
    parser.add_argument(
        '--cache-days', type=int, default=30,
        help='Number of days to consider cache fresh (default: 30)'
    )
    
    parser.add_argument(
        '--refresh-topics', action='store_true',
        help='Force refresh topics cache (default: False)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize parser
        books_parser = OReillyBooksParser(
            use_auth=args.use_auth,
            output_dir=args.output
        )
        
        # Parse books
        results = books_parser.parse_all_books(
            max_pages_per_topic=args.max_pages,
            output_format=args.format,
            force_update=args.force_update,
            cache_days=args.cache_days,
            refresh_topics=args.refresh_topics
        )
        
        if results:
            print(f"\n✅ Successfully parsed {results['total_books']} books from {results['total_topics']} topics!")
            print(f"📁 Results saved to: {args.output}/")
        else:
            print("❌ No results found.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Parsing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()