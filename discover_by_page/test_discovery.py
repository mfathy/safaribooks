#!/usr/bin/env python3
"""
Test script for the Books by Page Discovery system
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from discover_by_page.discover_books_by_page import BooksByPageDiscoverer


def test_basic_functionality():
    """Test basic functionality with a small page range"""
    print("Testing Books by Page Discovery...")
    
    # Initialize discoverer
    discoverer = BooksByPageDiscoverer()
    
    # Test with just a few pages
    print("Testing API call and validation...")
    try:
        # Test API call
        response = discoverer._search_oreilly_api(1)
        print(f"✅ API call successful. Found {len(response.get('results', []))} results on page 1")
        
        # Test validation
        results = response.get('results', [])
        valid_books = 0
        for item in results:
            if discoverer._validate_book(item):
                valid_books += 1
        
        print(f"✅ Validation working. {valid_books} valid books found on page 1")
        
        # Test topic extraction
        if valid_books > 0:
            for item in results:
                if discoverer._validate_book(item):
                    book_info = discoverer._extract_book_info(item)
                    print(f"✅ Book extraction working. Example: {book_info['title'][:50]}...")
                    print(f"   Main topic: {book_info['main_topic']}")
                    print(f"   Secondary topics: {book_info['secondary_topics']}")
                    break
        
        print("✅ All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_small_discovery():
    """Test discovery with a very small range"""
    print("\nTesting small discovery (pages 1-2)...")
    
    discoverer = BooksByPageDiscoverer()
    
    try:
        results = discoverer.discover_books_by_page(1, 2)
        print(f"✅ Small discovery completed!")
        print(f"   Pages processed: {results['pages_processed']}")
        print(f"   Books discovered: {results['total_books_discovered']}")
        print(f"   Topics created: {results['topics_created']}")
        print(f"   Duplicates skipped: {results['duplicates_skipped']}")
        
        # Check if topic files were created
        topic_files = list(discoverer.book_ids_dir.glob("*_books.json"))
        print(f"   Topic files created: {len(topic_files)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Small discovery test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("BOOKS BY PAGE DISCOVERY TEST")
    print("=" * 60)
    
    # Test basic functionality
    basic_test = test_basic_functionality()
    
    if basic_test:
        # Test small discovery
        discovery_test = test_small_discovery()
        
        if discovery_test:
            print("\n🎉 All tests passed! The discovery system is working correctly.")
            print("\nTo run the full discovery:")
            print("cd discover_by_page")
            print("python3 discover_books_by_page.py --start-page 1 --end-page 10 --verbose")
        else:
            print("\n❌ Discovery test failed.")
    else:
        print("\n❌ Basic functionality test failed.")

