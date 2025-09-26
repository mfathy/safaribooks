#!/usr/bin/env python3
"""
Test the format=book parameter to see if it affects results
"""

import requests
import json

def test_format_parameter():
    print("🔍 Testing format=book parameter impact")
    print("=" * 60)
    
    base_url = "https://learning.oreilly.com/api/v2/search/"
    topic = "programming-languages"
    
    # Test different URL variations
    test_urls = [
        {
            "name": "Without format parameter",
            "url": f"{base_url}?topic={topic}&page=1&limit=100"
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
            "name": "With content_type=book",
            "url": f"{base_url}?topic={topic}&page=1&limit=100&content_type=book"
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
                
                # Check content types in results
                content_types = {}
                for item in results[:5]:  # Check first 5 items
                    content_type = item.get('content_type', 'unknown')
                    content_types[content_type] = content_types.get(content_type, 0) + 1
                
                print(f"📚 Content types in first 5 results: {content_types}")
                
                # Show first item details
                if results:
                    first_item = results[0]
                    print(f"📖 First item:")
                    print(f"   Title: {first_item.get('title', 'No title')}")
                    print(f"   Content Type: {first_item.get('content_type', 'No type')}")
                    print(f"   Format: {first_item.get('format', 'No format')}")
                    print(f"   ID: {first_item.get('archive_id', 'No ID')}")
                
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == '__main__':
    test_format_parameter()
