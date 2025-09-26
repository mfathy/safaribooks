#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Book Parser Script
Extracts book information and IDs from O'Reilly Learning topics

Usage:
    python main_parser.py topic <topic-name> [options]
    python main_parser.py all-topics [options]
"""

import os
import sys
import argparse
from pathlib import Path

# Add the book_parser directory to Python path
parser_dir = Path(__file__).parent / "book_parser"
sys.path.insert(0, str(parser_dir))

# Import parser modules
from topic_book_parser import TopicBookParser
from oreilly_books_parser import OReillyBooksParser


def main():
    """Main function for the book parser"""
    parser = argparse.ArgumentParser(
        description='Parse O\'Reilly Learning books and extract book IDs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_parser.py topic generative-ai
  python main_parser.py topic python --max-pages 5 --delay 1.0
  python main_parser.py all-topics --output-dir results
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Topic-specific parser
    topic_parser = subparsers.add_parser('topic', help='Parse books for a specific topic')
    topic_parser.add_argument('topic_name', help='Topic slug (e.g., generative-ai, python, machine-learning)')
    topic_parser.add_argument('--max-pages', type=int, help='Maximum number of pages to fetch')
    topic_parser.add_argument('--page-size', type=int, default=100, help='Results per page (max 100)')
    topic_parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests (seconds)')
    topic_parser.add_argument('--no-auth', action='store_true', help='Skip authentication')
    topic_parser.add_argument('--output-dir', default='book_lists', help='Output directory')
    
    # All topics parser
    all_topics_parser = subparsers.add_parser('all-topics', help='Parse books for all available topics')
    all_topics_parser.add_argument('--max-pages', type=int, default=10, help='Maximum pages per topic')
    all_topics_parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
    all_topics_parser.add_argument('--no-auth', action='store_true', help='Skip authentication')
    all_topics_parser.add_argument('--output-dir', default='book_lists', help='Output directory')
    all_topics_parser.add_argument('--force-refresh', action='store_true', help='Force refresh of topic discovery')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    if args.command == 'topic':
        print(f"🚀 Starting topic parser for: {args.topic_name}")
        print("=" * 60)
        
        # Initialize topic parser
        topic_parser_instance = TopicBookParser(
            use_auth=not args.no_auth,
            output_dir=args.output_dir
        )
        
        # Fetch books for the topic
        results = topic_parser_instance.get_books_for_topic(
            topic_slug=args.topic_name,
            max_pages=args.max_pages,
            page_size=args.page_size,
            delay=args.delay
        )
        
        # Display results
        print(f"\n📊 Results for topic '{args.topic_name}':")
        print(f"   Books found: {results['total_books_found']}")
        print(f"   Unique book IDs: {results['unique_book_ids']}")
        print(f"   API total count: {results['total_count_from_api']}")
        print(f"   Pages fetched: {results['pages_fetched']}")
        print(f"   API errors: {results['api_errors']}")
        
        if results.get('page_limit_reached', False):
            print(f"   ⚠️  Page limit reached: Only first 10 pages available")
        
        # Verify results
        verification = topic_parser_instance.verify_results(results)
        print(f"\n🔍 Verification:")
        print(f"   Coverage: {verification['coverage']:.1f}%")
        print(f"   Duplicates: {verification['duplicates']}")
        print(f"   Missing: {verification['missing_ids']}")
        
        if verification.get('note'):
            print(f"   Note: {verification['note']}")
        
        # Save results
        topic_parser_instance.save_results(results, args.topic_name)
        
        print(f"\n✅ Complete! Check the '{args.output_dir}' directory for results.")
    
    elif args.command == 'all-topics':
        print("🚀 Starting all-topics parser")
        print("=" * 60)
        
        # Initialize all-topics parser
        all_topics_parser_instance = OReillyBooksParser(
            use_auth=not args.no_auth,
            output_dir=args.output_dir
        )
        
        # Discover topics
        print("🔍 Discovering available topics...")
        topics = all_topics_parser_instance.discover_topics(force_refresh=args.force_refresh)
        print(f"📚 Found {len(topics)} topics")
        
        # Parse each topic
        for i, topic in enumerate(topics, 1):
            topic_slug = topic['slug']
            topic_title = topic['title']
            
            print(f"\n📖 Processing topic {i}/{len(topics)}: {topic_title} ({topic_slug})")
            print("-" * 50)
            
            try:
                # Create topic-specific parser
                topic_parser = TopicBookParser(
                    use_auth=not args.no_auth,
                    output_dir=os.path.join(args.output_dir, 'topics')
                )
                
                # Fetch books for this topic
                results = topic_parser.get_books_for_topic(
                    topic_slug=topic_slug,
                    max_pages=args.max_pages,
                    delay=args.delay
                )
                
                print(f"   ✅ Found {results['total_books_found']} books")
                
                # Save results
                topic_parser.save_results(results, topic_slug)
                
            except Exception as e:
                print(f"   ❌ Error processing {topic_slug}: {e}")
                continue
        
        print(f"\n✅ All topics processed! Check the '{args.output_dir}' directory for results.")


if __name__ == "__main__":
    main()
