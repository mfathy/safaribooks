#!/usr/bin/env python3
"""
Get All Python Books from O'Reilly Learning
This script searches for all Python-related books available on O'Reilly Learning
and saves the results to JSON and text files.
"""

import sys
import os
import json
import time
from datetime import datetime

# Add the oreilly_parser directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'oreilly_parser'))

from oreilly_books_parser import load_cookies, search_oreilly_learning_api_with_pagination, save_books_info_to_json

def get_all_python_books():
    """Get all Python books from O'Reilly Learning"""
    print("🐍 O'Reilly Learning - All Python Books")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load authentication cookies
    cookies = load_cookies()
    if not cookies:
        print("❌ No authentication cookies found!")
        print("Please make sure cookies.json exists with valid O'Reilly Learning cookies")
        print("You can get cookies by:")
        print("1. Logging into learning.oreilly.com in your browser")
        print("2. Using browser dev tools to copy cookies")
        print("3. Saving them to cookies.json file")
        return False
    
    print("✅ Authentication cookies loaded")
    
    # Search for all Python books (no page limit)
    print("\n🔍 Searching for ALL Python books...")
    print("⚠️  This may take a while as it will fetch all available pages...")
    
    start_time = time.time()
    
    try:
        book_ids = search_oreilly_learning_api_with_pagination(
            'Python', 
            'https://learning.oreilly.com/search/skills/python/', 
            cookies, 
            max_pages=None,  # No limit - get all pages
            verbose=True
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n🎉 Search completed!")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📚 Found {len(book_ids)} unique Python books")
        
        # Save book IDs to text file
        if book_ids:
            with open('python-books-ids.txt', 'w') as f:
                f.write('\n'.join(book_ids))
            print(f"💾 Book IDs saved to: python-books-ids.txt")
        
        # The detailed book info is already saved by the parser
        print(f"💾 Detailed book info saved to: python-books-info.json")
        
        # Show summary statistics
        print(f"\n📊 Summary:")
        print(f"   📚 Total Python books found: {len(book_ids)}")
        print(f"   ⏱️  Search duration: {duration:.1f} seconds")
        print(f"   📄 Average time per book: {duration/len(book_ids):.2f} seconds" if book_ids else "   📄 No books found")
        
        return True
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Search interrupted by user")
        print(f"📊 Partial results may be available in python-books-info.json")
        return False
    except Exception as e:
        print(f"\n❌ Error during search: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python3 get_all_python_books.py")
        print("\nThis script will:")
        print("  - Search for ALL Python books on O'Reilly Learning")
        print("  - Save book IDs to python-books-ids.txt")
        print("  - Save detailed book info to python-books-info.json")
        print("  - Show progress and statistics")
        print("\nRequirements:")
        print("  - Valid cookies.json file with O'Reilly Learning authentication")
        return
    
    success = get_all_python_books()
    
    if success:
        print(f"\n✅ All Python books retrieved successfully!")
        print(f"📁 Check the generated files for results")
    else:
        print(f"\n❌ Failed to retrieve Python books")
        sys.exit(1)

if __name__ == "__main__":
    main()
