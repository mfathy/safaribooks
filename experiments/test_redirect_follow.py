#!/usr/bin/env python3
"""
Follow redirects to see if they lead to download URLs
"""

import requests
import json

def test_redirect_follow():
    print("🔍 Following redirects to find download URLs")
    print("=" * 60)
    
    # Get a sample book
    api_url = "https://learning.oreilly.com/api/v2/search/?topic=programming-languages&page=1&limit=1"
    
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
        
        if not results:
            print("❌ No results found")
            return
        
        book = results[0]
        book_id = book.get('archive_id') or book.get('isbn')
        book_title = book.get('title', 'Unknown')
        
        print(f"📖 Testing book: {book_title}")
        print(f"   ID: {book_id}")
        print()
        
        # Test URLs that returned 307 redirects
        test_urls = [
            f"https://learning.oreilly.com/library/view/book/{book_id}/",
            f"https://learning.oreilly.com/library/view/book/{book_id}/epub/",
            f"https://learning.oreilly.com/library/view/book/{book_id}/download/",
        ]
        
        for url in test_urls:
            print(f"🔗 Testing: {url}")
            try:
                # Follow redirects
                response = requests.get(url, headers=headers, allow_redirects=True)
                print(f"   Final URL: {response.url}")
                print(f"   Status: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
                print(f"   Content-Length: {response.headers.get('content-length', 'unknown')}")
                
                # Check if it's a download URL
                if 'download' in response.url.lower() or 'epub' in response.url.lower():
                    print(f"   ✅ Looks like a download URL!")
                elif response.headers.get('content-type', '').startswith('application/'):
                    print(f"   ✅ Binary content detected!")
                else:
                    print(f"   ❌ Not a download URL")
                
                print()
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                print()
        
        # Test the API v1 book endpoint
        api_v1_url = f"https://learning.oreilly.com/api/v1/book/{book_id}/"
        print(f"🔗 Testing API v1 book endpoint: {api_v1_url}")
        try:
            response = requests.get(api_v1_url, headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                book_data = response.json()
                print(f"   📋 Available fields: {list(book_data.keys())}")
                
                # Look for download-related fields
                download_fields = [k for k in book_data.keys() if 'download' in k.lower() or 'epub' in k.lower() or 'pdf' in k.lower()]
                if download_fields:
                    print(f"   🔗 Download fields found: {download_fields}")
                    for field in download_fields:
                        print(f"      {field}: {book_data[field]}")
                else:
                    print(f"   ❌ No download fields found")
            else:
                print(f"   ❌ API v1 endpoint failed")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == '__main__':
    test_redirect_follow()
