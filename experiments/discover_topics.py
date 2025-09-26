#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
O'Reilly Topics Discovery Script
Discovers and caches all available topics from O'Reilly Learning

@author: SafariBooks Team
"""

import os
import sys
import json
import argparse
from datetime import datetime
from urllib.parse import urljoin
from lxml import html
from typing import List, Dict

# Import our modular components
from auth import AuthManager
from display import Display
from config import SAFARI_BASE_URL, HEADERS

class TopicsDiscoverer:
    """Discovers and caches topics from O'Reilly Learning"""
    
    def __init__(self, use_auth: bool = True, output_dir: str = "topics"):
        self.use_auth = use_auth
        self.output_dir = output_dir
        self.display = Display("topics_discovery.log", os.path.dirname(os.path.realpath(__file__)))
        self.session = None
        self.auth_manager = None
        
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
            self.display.info(f"📊 API Response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    api_data = response.json()
                    self.display.info(f"📝 API Response type: {type(api_data)}")
                    
                    if isinstance(api_data, list):
                        for topic in api_data:
                            if isinstance(topic, dict) and 'slug' in topic:
                                topics.append({
                                    'slug': topic['slug'],
                                    'title': topic.get('title', topic['slug'].replace('-', ' ').title()),
                                    'url': f"{SAFARI_BASE_URL}/search/topics/{topic['slug']}"
                                })
                    elif isinstance(api_data, dict):
                        # Handle dict response format
                        if 'results' in api_data:
                            for topic in api_data['results']:
                                if isinstance(topic, dict) and 'slug' in topic:
                                    topics.append({
                                        'slug': topic['slug'],
                                        'title': topic.get('title', topic['slug'].replace('-', ' ').title()),
                                        'url': f"{SAFARI_BASE_URL}/search/topics/{topic['slug']}"
                                    })
                    
                    self.display.info(f"✅ Found {len(topics)} topics from API")
                except json.JSONDecodeError as e:
                    self.display.info(f"❌ API response not JSON: {e}")
                    self.display.info("🌐 Trying HTML parsing...")
            
            # Method 2: If API fails, try HTML parsing
            if not topics:
                self.display.info("🌐 Trying HTML parsing from topics page...")
                topics_url = f"{SAFARI_BASE_URL}/topics/"
                response = self.session.get(topics_url)
                
                self.display.info(f"📊 HTML Response status: {response.status_code}")
                
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
                        self.display.info(f"🔍 Found {len(links)} links with selector: {selector}")
                        
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
                'count': len(topics),
                'discovery_method': 'api' if len(topics) > 20 else 'predefined'
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.display.error(f"Failed to cache topics: {e}")
    
    def save_topics_formats(self, topics: List[Dict[str, str]]):
        """Save topics in multiple formats"""
        # Save as JSON
        json_file = os.path.join(self.output_dir, "topics.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(topics, f, indent=2, ensure_ascii=False)
        self.display.info(f"💾 Topics saved to: {json_file}")
        
        # Save as CSV
        csv_file = os.path.join(self.output_dir, "topics.csv")
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("slug,title,url\n")
            for topic in topics:
                f.write(f"{topic['slug']},{topic['title']},{topic['url']}\n")
        self.display.info(f"💾 Topics saved to: {csv_file}")
        
        # Save as TXT (simple list)
        txt_file = os.path.join(self.output_dir, "topics.txt")
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("O'Reilly Learning Topics\n")
            f.write("=" * 50 + "\n\n")
            for i, topic in enumerate(topics, 1):
                f.write(f"{i:2d}. {topic['title']} ({topic['slug']})\n")
                f.write(f"    URL: {topic['url']}\n\n")
        self.display.info(f"💾 Topics saved to: {txt_file}")
        
        # Save as markdown
        md_file = os.path.join(self.output_dir, "topics.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# O'Reilly Learning Topics\n\n")
            f.write(f"**Total Topics:** {len(topics)}\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Topics List\n\n")
            for i, topic in enumerate(topics, 1):
                f.write(f"{i}. **{topic['title']}** (`{topic['slug']}`)\n")
                f.write(f"   - URL: {topic['url']}\n\n")
        self.display.info(f"💾 Topics saved to: {md_file}")
    
    def display_topics_summary(self, topics: List[Dict[str, str]]):
        """Display a summary of discovered topics"""
        self.display.info("=" * 60)
        self.display.info("TOPICS DISCOVERY SUMMARY")
        self.display.info("=" * 60)
        self.display.info(f"Total Topics Found: {len(topics)}")
        self.display.info(f"Output Directory: {self.output_dir}")
        self.display.info("")
        
        # Group topics by category
        categories = {}
        for topic in topics:
            # Simple categorization based on slug
            if 'programming' in topic['slug'] or topic['slug'] in ['python', 'javascript', 'java']:
                category = 'Programming'
            elif 'data' in topic['slug'] or 'machine' in topic['slug'] or 'ai' in topic['slug']:
                category = 'Data & AI'
            elif 'cloud' in topic['slug'] or topic['slug'] in ['aws', 'azure', 'google-cloud', 'docker', 'kubernetes']:
                category = 'Cloud & DevOps'
            elif 'web' in topic['slug'] or 'mobile' in topic['slug']:
                category = 'Web & Mobile'
            elif topic['slug'] in ['business', 'career-development']:
                category = 'Business & Career'
            else:
                category = 'Other'
            
            if category not in categories:
                categories[category] = []
            categories[category].append(topic)
        
        for category, category_topics in categories.items():
            self.display.info(f"📂 {category}: {len(category_topics)} topics")
            for topic in category_topics[:5]:  # Show first 5
                self.display.info(f"   • {topic['title']} ({topic['slug']})")
            if len(category_topics) > 5:
                self.display.info(f"   ... and {len(category_topics) - 5} more")
            self.display.info("")


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="O'Reilly Topics Discovery Script - Discover and cache all available topics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 discover_topics.py                    # Discover topics with authentication
  python3 discover_topics.py --no-auth          # Discover topics without authentication
  python3 discover_topics.py --output my_topics # Save to custom directory
  python3 discover_topics.py --force-refresh    # Force refresh topics cache
  python3 discover_topics.py --list-only        # Just list topics, don't save files

Features:
  - Multi-method discovery: API, HTML parsing, predefined fallback
  - Smart caching: 7-day cache freshness
  - Multiple output formats: JSON, CSV, TXT, Markdown
  - Detailed logging and progress indication
        """
    )
    
    parser.add_argument(
        '--no-auth', dest='use_auth', action='store_false',
        help='Run without authentication (may have limited access)'
    )
    
    parser.add_argument(
        '--output', default='topics',
        help='Output directory for topics files (default: topics)'
    )
    
    parser.add_argument(
        '--force-refresh', action='store_true',
        help='Force refresh topics cache (default: False)'
    )
    
    parser.add_argument(
        '--list-only', action='store_true',
        help='Just list topics, don\'t save files (default: False)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize discoverer
        discoverer = TopicsDiscoverer(
            use_auth=args.use_auth,
            output_dir=args.output
        )
        
        # Discover topics
        topics = discoverer.discover_topics(force_refresh=args.force_refresh)
        
        if topics:
            # Display summary
            discoverer.display_topics_summary(topics)
            
            # Save topics in multiple formats
            if not args.list_only:
                discoverer.save_topics_formats(topics)
            
            print(f"\n✅ Successfully discovered {len(topics)} topics!")
            print(f"📁 Results saved to: {args.output}/")
        else:
            print("❌ No topics discovered!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Discovery interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

