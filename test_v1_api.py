#!/usr/bin/env python3
"""Test the v1 API endpoint"""
import requests
import json

# Load cookies
with open('cookies.json', 'r') as f:
    cookies = json.load(f)

# Try v1 API
url = "https://learning.oreilly.com/api/v1/search"
params = {
    'q': 'Engineering Leadership',
    'rows': 10
}

headers = {
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
}

print("Testing v1 API...")
print(f"URL: {url}")
print(f"Params: {params}")

response = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=30)

print(f"\nStatus Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    results = data.get('results', [])
    print(f"Total results: {len(results)}")
    
    if results:
        print(f"\nFirst result:")
        print(f"  Title: {results[0].get('title', 'N/A')}")
        print(f"  Archive ID: {results[0].get('archive_id', 'N/A')}")
        print(f"  URL: {results[0].get('url', 'N/A')}")
        
        print(f"\n✅ API IS WORKING!")
        print(f"Sample keys in result: {list(results[0].keys())[:10]}")
else:
    print(f"Error: {response.text[:200]}")

