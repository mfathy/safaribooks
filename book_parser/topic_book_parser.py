#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Topic-Specific Book Parser for O'Reilly Learning
Fetches and parses book IDs for a specific topic from O'Reilly Learning API

@author: Enhanced by SafariBooks Team
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Set, Optional, Any
from urllib.parse import urljoin, urlparse

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


class TopicBookParser:
    """Parser for extracting book IDs from a specific O'Reilly Learning topic"""
    
    def __init__(self, use_auth=True, output_dir="topic_results"):
        self.use_auth = use_auth
        self.output_dir = output_dir
        self.session = None
        self.display = Display("topic_parser.log", os.path.dirname(os.path.realpath(__file__)))
        
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
    
    def get_books_for_topic(self, topic_slug: str, max_pages: int = None, 
                          page_size: int = 100, delay: float = 0.5) -> Dict[str, Any]:
        """
        Get all books for a specific topic
        
        Args:
            topic_slug: Topic slug (e.g., 'generative-ai', 'python', 'machine-learning')
            max_pages: Maximum number of pages to fetch (None for all)
            page_size: Number of results per page (max 100)
            delay: Delay between requests in seconds
            
        Returns:
            Dictionary containing book data, metadata, and statistics
        """
        self.display.info(f"🔍 Fetching books for topic: {topic_slug}")
        
        all_books = []
        book_ids = set()
        page = 1
        total_count = 0
        api_errors = 0
        
        # API endpoint
        base_url = f"{SAFARI_BASE_URL}/api/v2/search/"
        
        while True:
            if max_pages and page > max_pages:
                self.display.info(f"📄 Reached maximum pages limit: {max_pages}")
                break
                
            # Construct API URL
            params = {
                'topic': topic_slug,
                'page': page,
                'limit': page_size
            }
            
            url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
            
            self.display.info(f"📡 Fetching page {page} from: {url}")
            
            try:
                response = self.session.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    total_count = data.get('total', 0)  # API uses 'total' not 'count'
                    next_page = data.get('next')
                    
                    self.display.info(f"✅ Page {page}: Found {len(results)} books")
                    
                    if not results:
                        self.display.info("📄 No more results found")
                        break
                    
                    # Extract book IDs and store book data
                    for book in results:
                        book_id = self._extract_book_id(book)
                        if book_id:
                            book_ids.add(book_id)
                            
                            # Safely extract authors
                            authors = []
                            if isinstance(book, dict) and 'authors' in book:
                                if isinstance(book['authors'], list):
                                    authors = [author.get('name', 'Unknown') if isinstance(author, dict) else str(author) for author in book['authors']]
                                else:
                                    authors = [str(book['authors'])]
                            
                            all_books.append({
                                'book_id': book_id,
                                'title': book.get('title', 'Unknown') if isinstance(book, dict) else str(book),
                                'authors': authors,
                                'isbn': book.get('isbn', '') if isinstance(book, dict) else '',
                                'issued': book.get('issued', '') if isinstance(book, dict) else '',
                                'url': book.get('id', '') if isinstance(book, dict) else '',
                                'archive_id': book.get('archive_id', '') if isinstance(book, dict) else ''
                            })
                    
                    # Check if there's a next page
                    if not next_page:
                        self.display.info("📄 No next page available")
                        break
                    
                    page += 1
                    
                    # Add delay to avoid rate limiting
                    if delay > 0:
                        time.sleep(delay)
                        
                elif response.status_code == 404:
                    self.display.error(f"❌ Topic '{topic_slug}' not found (404)")
                    break
                elif response.status_code == 429:
                    self.display.warning(f"⚠️  Rate limited (429). Waiting {delay * 2} seconds...")
                    time.sleep(delay * 2)
                    continue
                else:
                    # Check for specific error messages
                    response_text = response.text.lower()
                    if "results past page 10 are unavailable to unauthorized users" in response_text:
                        self.display.warning(f"⚠️  Reached page limit for unauthorized users (page {page})")
                        self.display.info("📄 Only first 10 pages are available without full authentication")
                        break
                    elif "unauthorized" in response_text or "authentication" in response_text:
                        self.display.warning(f"⚠️  Authentication required for page {page}")
                        break
                    else:
                        self.display.error(f"❌ API error {response.status_code}: {response.text}")
                        api_errors += 1
                        if api_errors > 5:
                            self.display.error("❌ Too many API errors, stopping")
                            break
                        time.sleep(delay * 2)
                        continue
                    
            except Exception as e:
                self.display.error(f"❌ Exception fetching page {page}: {e}")
                api_errors += 1
                if api_errors > 5:
                    self.display.error("❌ Too many errors, stopping")
                    break
                time.sleep(delay * 2)
                continue
        
        # Check if we hit the page limit
        page_limit_reached = page > 10
        if page_limit_reached:
            self.display.warning(f"⚠️  Reached page limit (page {page-1}). Only first 10 pages available.")
        
        # Compile results
        result = {
            'topic': topic_slug,
            'total_books_found': len(all_books),
            'unique_book_ids': len(book_ids),
            'total_count_from_api': total_count,
            'pages_fetched': page - 1,
            'api_errors': api_errors,
            'page_limit_reached': page_limit_reached,
            'books': all_books,
            'book_ids': list(book_ids),
            'fetched_at': datetime.now().isoformat(),
            'api_endpoint': base_url
        }
        
        return result
    
    def _extract_book_id(self, book_data: Dict[str, Any]) -> Optional[str]:
        """Extract book ID from book data"""
        # Try different fields that might contain the book ID
        book_id = None
        
        # Method 1: From archive_id
        if book_data.get('archive_id'):
            book_id = str(book_data['archive_id'])
        
        # Method 2: From ISBN
        elif book_data.get('isbn'):
            book_id = str(book_data['isbn'])
        
        # Method 3: Extract from URL
        elif book_data.get('id'):
            url = book_data['id']
            # Extract ID from URL like: https://www.safaribooksonline.com/api/v1/book/9781098166298/
            import re
            match = re.search(r'/book/(\d+)/', url)
            if match:
                book_id = match.group(1)
        
        return book_id
    
    def save_results(self, results: Dict[str, Any], topic_slug: str):
        """Save results to JSON files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save complete results
        complete_file = os.path.join(self.output_dir, f"{topic_slug}_complete_{timestamp}.json")
        with open(complete_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save just book IDs
        book_ids_file = os.path.join(self.output_dir, f"{topic_slug}_book_ids_{timestamp}.json")
        book_ids_data = {
            'topic': topic_slug,
            'book_ids': results['book_ids'],
            'count': len(results['book_ids']),
            'fetched_at': results['fetched_at']
        }
        with open(book_ids_file, 'w', encoding='utf-8') as f:
            json.dump(book_ids_data, f, indent=2, ensure_ascii=False)
        
        # Save summary
        summary_file = os.path.join(self.output_dir, f"{topic_slug}_summary_{timestamp}.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"Topic: {topic_slug}\n")
            f.write(f"Total books found: {results['total_books_found']}\n")
            f.write(f"Unique book IDs: {results['unique_book_ids']}\n")
            f.write(f"API total count: {results['total_count_from_api']}\n")
            f.write(f"Pages fetched: {results['pages_fetched']}\n")
            f.write(f"API errors: {results['api_errors']}\n")
            f.write(f"Fetched at: {results['fetched_at']}\n\n")
            
            f.write("Sample books:\n")
            for i, book in enumerate(results['books'][:10]):  # First 10 books
                f.write(f"{i+1}. {book['title']} by {', '.join(book['authors'])}\n")
                f.write(f"   Book ID: {book['book_id']}\n")
                f.write(f"   ISBN: {book['isbn']}\n\n")
        
        self.display.info(f"💾 Results saved:")
        self.display.info(f"   Complete: {complete_file}")
        self.display.info(f"   Book IDs: {book_ids_file}")
        self.display.info(f"   Summary: {summary_file}")
    
    def verify_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Verify the results and provide analysis"""
        verification = {
            'topic': results['topic'],
            'books_found': results['total_books_found'],
            'unique_ids': results['unique_book_ids'],
            'api_total': results['total_count_from_api'],
            'coverage': 0.0,
            'duplicates': 0,
            'missing_ids': 0,
            'page_limit_reached': results.get('page_limit_reached', False),
            'sample_books': results['books'][:5] if results['books'] else []
        }
        
        # Calculate coverage
        if results['total_count_from_api'] > 0:
            verification['coverage'] = (results['total_books_found'] / results['total_count_from_api']) * 100
        
        # Check for duplicates
        book_ids = [book['book_id'] for book in results['books']]
        unique_ids = set(book_ids)
        verification['duplicates'] = len(book_ids) - len(unique_ids)
        
        # Check for missing IDs
        verification['missing_ids'] = results['total_count_from_api'] - results['total_books_found']
        
        # Add page limit warning
        if verification['page_limit_reached']:
            verification['note'] = "Limited to first 10 pages due to authentication restrictions"
        
        return verification


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Parse O\'Reilly Learning books for a specific topic')
    parser.add_argument('topic', help='Topic slug (e.g., generative-ai, python, machine-learning)')
    parser.add_argument('--max-pages', type=int, help='Maximum number of pages to fetch')
    parser.add_argument('--page-size', type=int, default=100, help='Results per page (max 100)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests (seconds)')
    parser.add_argument('--no-auth', action='store_true', help='Skip authentication')
    parser.add_argument('--output-dir', default='topic_results', help='Output directory')
    
    args = parser.parse_args()
    
    # Initialize parser
    parser_instance = TopicBookParser(
        use_auth=not args.no_auth,
        output_dir=args.output_dir
    )
    
    print(f"🚀 Starting topic book parser for: {args.topic}")
    print("=" * 60)
    
    # Fetch books
    results = parser_instance.get_books_for_topic(
        topic_slug=args.topic,
        max_pages=args.max_pages,
        page_size=args.page_size,
        delay=args.delay
    )
    
    # Display results
    print(f"\n📊 Results for topic '{args.topic}':")
    print(f"   Books found: {results['total_books_found']}")
    print(f"   Unique book IDs: {results['unique_book_ids']}")
    print(f"   API total count: {results['total_count_from_api']}")
    print(f"   Pages fetched: {results['pages_fetched']}")
    print(f"   API errors: {results['api_errors']}")
    
    if results.get('page_limit_reached', False):
        print(f"   ⚠️  Page limit reached: Only first 10 pages available")
    
    # Verify results
    verification = parser_instance.verify_results(results)
    print(f"\n🔍 Verification:")
    print(f"   Coverage: {verification['coverage']:.1f}%")
    print(f"   Duplicates: {verification['duplicates']}")
    print(f"   Missing: {verification['missing_ids']}")
    
    if verification.get('note'):
        print(f"   Note: {verification['note']}")
    
    # Save results
    parser_instance.save_results(results, args.topic)
    
    print(f"\n✅ Complete! Check the '{args.output_dir}' directory for results.")


if __name__ == "__main__":
    main()
