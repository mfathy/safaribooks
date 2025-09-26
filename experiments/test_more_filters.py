#!/usr/bin/env python3
"""
Test more filter parameters to see if we can get only books
"""

import requests
import json

def test_more_filters():
    print("🔍 Testing more filter parameters")
    print("=" * 60)
    
    base_url = "https://learning.oreilly.com/api/v2/search/"
    topic = "programming-languages"
    
    # Test different filter combinations
    test_urls = [
        {
            "name": "No filters (current)",
            "url": f"{base_url}?topic={topic}&page=1&limit=100"
        },
        {
            "name": "With content_type=book",
            "url": f"{base_url}?topic={topic}&page=1&limit=100&content_type=book"
        },
        {
            "name": "With format=book",
            "url": f"{base_url}?topic={topic}&page=1&limit=100&format=book"
        },
        {
            "name": "With type=book",
            "url": f"{base_url}?topic={topic}&page=1&limit=100&type=book"
        },
        {
            "name": "With content_format=book",
            "url": f"{base_url}?topic={topic}&page=1&limit=100&content_format=book"
        },
        {
            "name": "With source=book",
            "url": f"{base_url}?topic={topic}&page=1&limit=100&source=book"
        }
    ]
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for test in test_urls:
        print(f"\n📊 Testing: {test['name']}")
        print(f"URL: {test['url']}")
        
        try:
            response = requests.get(test['url'], headers=headers)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                total = data.get('total', 0)
                
                print(f"✅ Results: {len(results)} items")
                print(f"📈 Total available: {total}")
                
                # Check content types in all results
                content_types = {}
                formats = {}
                sources = {}
                
                for item in results:
                    content_type = item.get('content_type', 'unknown')
                    format_type = item.get('format', 'unknown')
                    source = item.get('source', 'unknown')
                    
                    content_types[content_type] = content_types.get(content_type, 0) + 1
                    formats[format_type] = formats.get(format_type, 0) + 1
                    sources[source] = sources.get(source, 0) + 1
                
                print(f"📚 Content types: {content_types}")
                print(f"📄 Formats: {formats}")
                print(f"🔗 Sources: {sources}")
                
            else:
                print(f"❌ Error: {response.status_code}")
                if response.status_code != 404:
                    print(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == '__main__':
    test_more_filters()
