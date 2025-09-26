#!/usr/bin/env python3
"""
Test if the API provides direct EPUB download links
"""

import requests
import json

def test_epub_download_links():
    print("🔍 Testing EPUB download links in API response")
    print("=" * 60)
    
    # Get a sample book from the API
    api_url = "https://learning.oreilly.com/api/v2/search/?topic=programming-languages&page=1&limit=5"
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code != 200:
            print(f"❌ Failed to fetch API: {response.status_code}")
            return
        
        data = response.json()
        results = data.get('results', [])
        
        print(f"📚 Found {len(results)} books to analyze")
        print()
        
        for i, book in enumerate(results, 1):
            print(f"📖 Book {i}: {book.get('title', 'No title')}")
            print(f"   ID: {book.get('archive_id', 'No ID')}")
            print(f"   ISBN: {book.get('isbn', 'No ISBN')}")
            print(f"   Content Type: {book.get('content_type', 'No type')}")
            print(f"   Format: {book.get('format', 'No format')}")
            print(f"   Source: {book.get('source', 'No source')}")
            
            # Check for download-related fields
            download_fields = [
                'download_url', 'epub_url', 'pdf_url', 'download_link',
                'file_url', 'content_url', 'media_url', 'asset_url',
                'epub_download', 'pdf_download', 'download_path'
            ]
            
            found_downloads = []
            for field in download_fields:
                if field in book and book[field]:
                    found_downloads.append(f"{field}: {book[field]}")
            
            if found_downloads:
                print(f"   🔗 Download links found:")
                for link in found_downloads:
                    print(f"      {link}")
            else:
                print(f"   ❌ No direct download links found")
            
            # Check URL fields
            url_fields = ['url', 'web_url', 'content_url', 'media_url']
            print(f"   🌐 URL fields:")
            for field in url_fields:
                if field in book and book[field]:
                    print(f"      {field}: {book[field]}")
            
            # Show all available fields for analysis
            print(f"   📋 All available fields: {list(book.keys())}")
            print()
            
            # Only show first 2 books in detail
            if i >= 2:
                break
        
        # Test if we can construct download URLs
        print("🔧 Testing URL construction patterns:")
        print("=" * 40)
        
        if results:
            first_book = results[0]
            book_id = first_book.get('archive_id') or first_book.get('isbn')
            
            if book_id:
                # Common O'Reilly download URL patterns
                test_patterns = [
                    f"https://learning.oreilly.com/library/view/book/{book_id}/",
                    f"https://learning.oreilly.com/api/v2/content/{book_id}/download/",
                    f"https://learning.oreilly.com/api/v2/content/{book_id}/epub/",
                    f"https://learning.oreilly.com/api/v2/content/{book_id}/pdf/",
                    f"https://learning.oreilly.com/library/view/book/{book_id}/epub/",
                    f"https://learning.oreilly.com/library/view/book/{book_id}/download/",
                    f"https://learning.oreilly.com/content/{book_id}/epub/",
                    f"https://learning.oreilly.com/content/{book_id}/download/",
                ]
                
                for pattern in test_patterns:
                    print(f"   Testing: {pattern}")
                    try:
                        test_response = requests.head(pattern, headers=headers, timeout=5)
                        print(f"      Status: {test_response.status_code}")
                        if test_response.status_code == 200:
                            content_type = test_response.headers.get('content-type', 'unknown')
                            content_length = test_response.headers.get('content-length', 'unknown')
                            print(f"      ✅ Content-Type: {content_type}")
                            print(f"      📦 Content-Length: {content_length}")
                    except Exception as e:
                        print(f"      ❌ Error: {e}")
                    print()
    
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == '__main__':
    test_epub_download_links()
