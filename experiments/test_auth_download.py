#!/usr/bin/env python3
"""
Test download URLs with authentication
"""

import requests
import json
import os

def test_auth_download():
    print("🔍 Testing download URLs with authentication")
    print("=" * 60)
    
    # Check if we have cookies
    cookies_file = "cookies.json"
    if not os.path.exists(cookies_file):
        print("❌ No cookies.json found. Authentication required for download testing.")
        print("   Run the main parser with authentication first.")
        return
    
    # Load cookies
    try:
        with open(cookies_file, 'r') as f:
            cookies = json.load(f)
        
        print(f"✅ Loaded {len(cookies)} cookies")
        
    except Exception as e:
        print(f"❌ Failed to load cookies: {e}")
        return
    
    # Get a sample book
    api_url = "https://learning.oreilly.com/api/v2/search/?topic=programming-languages&page=1&limit=1"
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(api_url, headers=headers, cookies=cookies)
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
        
        # Test download URLs with authentication
        test_urls = [
            f"https://learning.oreilly.com/library/view/book/{book_id}/epub/",
            f"https://learning.oreilly.com/library/view/book/{book_id}/download/",
            f"https://learning.oreilly.com/api/v1/book/{book_id}/epub/",
            f"https://learning.oreilly.com/api/v1/book/{book_id}/download/",
        ]
        
        for url in test_urls:
            print(f"🔗 Testing: {url}")
            try:
                response = requests.get(url, headers=headers, cookies=cookies, allow_redirects=True)
                print(f"   Final URL: {response.url}")
                print(f"   Status: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
                print(f"   Content-Length: {response.headers.get('content-length', 'unknown')}")
                
                # Check if it's a download URL
                content_type = response.headers.get('content-type', '')
                if 'epub' in content_type or 'zip' in content_type or 'application/' in content_type:
                    print(f"   ✅ Download URL found!")
                    print(f"   📦 File size: {response.headers.get('content-length', 'unknown')} bytes")
                elif response.status_code == 200:
                    print(f"   ✅ Accessible URL")
                else:
                    print(f"   ❌ Not accessible")
                
                print()
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                print()
        
        # Test the API v1 book endpoint with auth
        api_v1_url = f"https://learning.oreilly.com/api/v1/book/{book_id}/"
        print(f"🔗 Testing API v1 book endpoint with auth: {api_v1_url}")
        try:
            response = requests.get(api_v1_url, headers=headers, cookies=cookies)
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
    test_auth_download()
