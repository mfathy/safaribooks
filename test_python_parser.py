#!/usr/bin/env python3
"""
Simple test script for Python books parser
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'oreilly_parser'))

from oreilly_books_parser import load_cookies, search_oreilly_learning_api_with_pagination

def test_python_books(pages=3):
    """Test the Python books parser with specified number of pages"""
    print("🐍 Python Books Parser Test")
    print("=" * 40)
    
    # Load authentication cookies
    cookies = load_cookies()
    if not cookies:
        print("❌ No authentication cookies found!")
        print("Please make sure cookies.json exists with valid O'Reilly Learning cookies")
        return False
    
    print("✅ Authentication cookies loaded")
    
    # Test with Python
    print(f"\n🔍 Searching for Python books (first {pages} pages)...")
    book_ids = search_oreilly_learning_api_with_pagination(
        'Python', 
        'https://learning.oreilly.com/search/skills/python/', 
        cookies, 
        max_pages=pages,
        verbose=True
    )
    
    print(f"\n🎉 Test completed!")
    print(f"📚 Found {len(book_ids)} unique Python books")
    print(f"💾 Results saved to: python-books-info.json")
    
    return True

if __name__ == "__main__":
    # Test with 3 pages by default
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    test_python_books(pages)
