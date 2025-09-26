#!/usr/bin/env python3
"""
Investigate O'Reilly API pagination and limits
"""

from auth import AuthManager
from display import Display
import os
import json

def investigate_api():
    display = Display('api_investigation.log', os.path.dirname(os.path.realpath(__file__)))
    auth = AuthManager(display)
    auth.initialize_session()

    print("🔍 Investigating O'Reilly API pagination and limits...")
    print("=" * 60)
    
    # Test different page sizes
    page_sizes = [15, 25, 50, 100, 200]
    topic = "programming-languages"
    
    print(f"\n📊 Testing different page sizes for topic: {topic}")
    print("-" * 50)
    
    for page_size in page_sizes:
        try:
            url = f"https://learning.oreilly.com/api/v1/search/?topic={topic}&page=1&page_size={page_size}"
            response = auth.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                total_count = data.get('count', 0)
                next_page = data.get('next')
                previous_page = data.get('previous')
                
                print(f"Page Size {page_size:3d}: {len(results):2d} results returned, Total: {total_count}")
                print(f"  Next page: {'Yes' if next_page else 'No'}")
                print(f"  Previous page: {'Yes' if previous_page else 'No'}")
                
                # Show first book title as example
                if results:
                    first_book = results[0]
                    print(f"  Example: {first_book.get('title', 'No title')[:50]}...")
            else:
                print(f"Page Size {page_size:3d}: Error {response.status_code}")
                
        except Exception as e:
            print(f"Page Size {page_size:3d}: Exception - {e}")
        print()
    
    # Test pagination limits
    print("\n📄 Testing pagination limits...")
    print("-" * 50)
    
    max_pages_to_test = 50
    page_size = 100  # Use the largest working page size
    
    total_found = 0
    last_page_with_results = 0
    
    for page in range(1, max_pages_to_test + 1):
        try:
            url = f"https://learning.oreilly.com/api/v1/search/?topic={topic}&page={page}&page_size={page_size}"
            response = auth.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                total_count = data.get('count', 0)
                next_page = data.get('next')
                
                if results:
                    total_found += len(results)
                    last_page_with_results = page
                    print(f"Page {page:2d}: {len(results):3d} results (Total so far: {total_found:4d})")
                else:
                    print(f"Page {page:2d}: No results - reached end")
                    break
                    
                if not next_page:
                    print(f"Page {page:2d}: No next page URL - API indicates end")
                    break
                    
            else:
                print(f"Page {page:2d}: Error {response.status_code}")
                break
                
        except Exception as e:
            print(f"Page {page:2d}: Exception - {e}")
            break
    
    print(f"\n📈 Summary:")
    print(f"  Total results found: {total_found}")
    print(f"  Last page with results: {last_page_with_results}")
    print(f"  Page size used: {page_size}")
    
    # Test if there are more results beyond our test
    if last_page_with_results > 0:
        print(f"\n🔍 Testing beyond page {last_page_with_results}...")
        for test_page in [last_page_with_results + 1, last_page_with_results + 5, last_page_with_results + 10]:
            try:
                url = f"https://learning.oreilly.com/api/v1/search/?topic={topic}&page={test_page}&page_size={page_size}"
                response = auth.session.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    print(f"  Page {test_page}: {len(results)} results")
                else:
                    print(f"  Page {test_page}: Error {response.status_code}")
                    break
            except Exception as e:
                print(f"  Page {test_page}: Exception - {e}")
                break
    
    # Test more pages to find the actual limit
    print(f"\n🔍 Testing more pages to find the actual limit...")
    print("-" * 50)
    
    total_found = 0
    for page in range(100, 300, 25):  # Test every 25 pages from 100 to 300
        try:
            url = f"https://learning.oreilly.com/api/v1/search/?topic={topic}&page={page}"
            response = auth.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                total_count = data.get('count', 0)
                
                if results:
                    total_found += len(results)
                    print(f"Page {page:3d}: {len(results):2d} results (Total: {total_found:4d})")
                else:
                    print(f"Page {page:3d}: No results - reached end")
                    break
            else:
                print(f"Page {page:3d}: Error {response.status_code}")
                break
        except Exception as e:
            print(f"Page {page:3d}: Exception - {e}")
            break
    
    print(f"Final total from extended test: {total_found} results")
    
    # Test different search parameters
    print(f"\n🔍 Testing different search parameters...")
    print("-" * 50)
    
    search_params = [
        f"?topic={topic}",
        f"?topic={topic}&page_size=100",
        f"?topic={topic}&page_size=100&page=1",
        f"?q=python&topic={topic}",
        f"?topic={topic}&sort=relevance",
        f"?topic={topic}&sort=date",
    ]
    
    for params in search_params:
        try:
            url = f"https://learning.oreilly.com/api/v1/search/{params}"
            response = auth.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                total_count = data.get('count', 0)
                print(f"Params: {params}")
                print(f"  Results: {len(results)}, Total: {total_count}")
            else:
                print(f"Params: {params} - Error {response.status_code}")
        except Exception as e:
            print(f"Params: {params} - Exception: {e}")
        print()

if __name__ == '__main__':
    investigate_api()
