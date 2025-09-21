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
from urllib.parse import urljoin, urlparse, parse_qs
from lxml import html, etree
from typing import List, Dict, Set, Optional, Tuple

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
    
    def discover_topics(self) -> List[Dict[str, str]]:
        """Discover all available topics/categories from O'Reilly Learning"""
        self.display.info("Discovering available topics...")
        
        topics = []
        
        # Main topics page
        topics_url = f"{SAFARI_BASE_URL}/topics/"
        
        try:
            response = self.session.get(topics_url)
            if response.status_code != 200:
                self.display.error(f"Failed to fetch topics page: {response.status_code}")
                return topics
            
            # Parse the topics page
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
            
            # Add some known popular topics if discovery didn't find them
            known_topics = {
                'programming-languages': 'Programming Languages',
                'software-development': 'Software Development',
                'web-mobile': 'Web & Mobile',
                'data-science': 'Data Science',
                'business': 'Business',
                'career-development': 'Career Development',
                'security': 'Security',
                'cloud-computing': 'Cloud Computing',
                'artificial-intelligence': 'Artificial Intelligence',
                'devops': 'DevOps'
            }
            
            existing_slugs = {topic['slug'] for topic in topics}
            for slug, title in known_topics.items():
                if slug not in existing_slugs:
                    topics.append({
                        'slug': slug,
                        'title': title,
                        'url': f"{SAFARI_BASE_URL}/search/topics/{slug}"
                    })
            
            self.display.info(f"Discovered {len(topics)} topics")
            return topics
            
        except Exception as e:
            self.display.error(f"Error discovering topics: {e}")
            return topics
    
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
    
    def get_books_for_topic(self, topic: Dict[str, str], max_pages: int = 100) -> List[Dict[str, str]]:
        """Get all book IDs for a specific topic using the API"""
        topic_slug = topic['slug']
        
        self.display.info(f"Fetching books for topic: {topic['title']} ({topic_slug})")
        
        all_books = []
        page = 1
        
        while page <= max_pages:
            try:
                # Use the search API endpoint
                api_url = f"{SAFARI_BASE_URL}/api/v1/search/?topic={topic_slug}&page={page}"
                
                response = self.session.get(api_url)
                if response.status_code != 200:
                    if page == 1:
                        self.display.error(f"Failed to fetch topic API: {response.status_code}")
                    break
                
                # Parse JSON response
                data = response.json()
                results = data.get('results', [])
                
                if not results:
                    # No more results, we've reached the end
                    break
                
                # Extract book information from API response
                for book in results:
                    book_id = book.get('archive_id') or book.get('isbn')
                    if book_id:
                        all_books.append({
                            'id': book_id,
                            'topic': topic_slug,
                            'topic_title': topic['title'],
                            'title': book.get('title', 'Unknown Title'),
                            'authors': ', '.join([author.get('name', '') for author in book.get('authors', [])]),
                            'isbn': book.get('isbn', ''),
                            'issued': book.get('issued', ''),
                            'url': f"{SAFARI_BASE_URL}/library/view/book/{book_id}/"
                        })
                
                self.display.info(f"  Page {page}: Found {len(results)} books")
                
                # Rate limiting
                time.sleep(0.5)
                page += 1
                
            except Exception as e:
                self.display.error(f"Error fetching page {page} for topic {topic_slug}: {e}")
                break
        
        self.display.info(f"Total books found for {topic['title']}: {len(all_books)}")
        return all_books
    
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
    
    def parse_all_books(self, max_pages_per_topic: int = 100, 
                       output_format: str = 'json') -> Dict[str, any]:
        """Main method to parse all books from all topics"""
        
        self.display.info("Starting O'Reilly Books Parser...")
        self.display.info(f"Output directory: {self.output_dir}")
        self.display.info(f"Max pages per topic: {max_pages_per_topic}")
        
        # Discover topics
        topics = self.discover_topics()
        if not topics:
            self.display.error("No topics discovered. Exiting.")
            return {}
        
        # Fetch books for each topic
        all_books = []
        for i, topic in enumerate(topics, 1):
            self.display.info(f"Processing topic {i}/{len(topics)}: {topic['title']}")
            
            try:
                topic_books = self.get_books_for_topic(topic, max_pages_per_topic)
                all_books.extend(topic_books)
                
                # Save intermediate results
                if i % 5 == 0:  # Save every 5 topics
                    self.save_results(all_books, topics[:i], output_format)
                
            except Exception as e:
                self.display.error(f"Error processing topic {topic['slug']}: {e}")
                continue
        
        # Save final results
        self.save_results(all_books, topics, output_format)
        
        # Display final summary
        self.display.info("=" * 50)
        self.display.info("PARSING COMPLETE")
        self.display.info("=" * 50)
        self.display.info(f"Total Topics Processed: {len(topics)}")
        self.display.info(f"Total Books Found: {len(all_books)}")
        self.display.info(f"Output Directory: {self.output_dir}")
        
        return {
            'topics': topics,
            'books': all_books,
            'total_topics': len(topics),
            'total_books': len(all_books)
        }


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Enhanced O'Reilly Books Parser - Fetch all book topics and IDs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 oreilly_books_parser.py                    # Parse all topics with authentication
  python3 oreilly_books_parser.py --no-auth          # Parse without authentication
  python3 oreilly_books_parser.py --max-pages 50     # Limit to 50 pages per topic
  python3 oreilly_books_parser.py --format csv       # Output as CSV format
  python3 oreilly_books_parser.py --output my_books  # Custom output directory
        """
    )
    
    parser.add_argument(
        '--no-auth', dest='use_auth', action='store_false',
        help='Run without authentication (may have limited access)'
    )
    parser.add_argument(
        '--max-pages', type=int, default=100,
        help='Maximum pages to fetch per topic (default: 100)'
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
            output_format=args.format
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