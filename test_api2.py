#!/usr/bin/env python3
"""Test different topic query formats"""
import requests
import json

# Load cookies
with open('cookies.json', 'r') as f:
    cookies = json.load(f)

url = "https://learning.oreilly.com/search/api/search/"
headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Referer': 'https://learning.oreilly.com/search/skills/engineering-leadership/?type=book&rows=100&language=en',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
}

# Try different parameter combinations
test_cases = [
    {
        'name': 'Original (with isTopics=true)',
        'params': {
            'type': 'book',
            'rows': 10,
            'language': 'en',
            'q': '*',
            'topics': 'Engineering Leadership',
            'isTopics': 'true',
        }
    },
    {
        'name': 'Without isTopics',
        'params': {
            'type': 'book',
            'rows': 10,
            'language': 'en',
            'q': '*',
            'topics': 'Engineering Leadership',
        }
    },
    {
        'name': 'With URL-encoded topic',
        'params': {
            'type': 'book',
            'rows': 10,
            'language': 'en',
            'q': '*',
            'topics': 'Engineering%20Leadership',
        }
    },
    {
        'name': 'With query in q parameter',
        'params': {
            'type': 'book',
            'rows': 10,
            'language': 'en',
            'q': 'topics:"Engineering Leadership"',
        }
    },
    {
        'name': 'With topic filter',
        'params': {
            'type': 'book',
            'rows': 10,
            'language': 'en',
            'q': '*',
            'topic': 'Engineering Leadership',
        }
    },
]

for test in test_cases:
    print(f"\n{'='*60}")
    print(f"Test: {test['name']}")
    print(f"{'='*60}")
    print(f"Params: {test['params']}")
    
    try:
        response = requests.get(url, params=test['params'], headers=headers, cookies=cookies, timeout=10)
        data = response.json()
        total = data.get('total', 0)
        results = data.get('results', [])
        
        print(f"Status: {response.status_code}")
        print(f"Total results: {total}")
        print(f"Results returned: {len(results)}")
        
        if results:
            print(f"\nFirst result:")
            print(f"  Title: {results[0].get('title', 'N/A')}")
            print(f"  ID: {results[0].get('archive_id', 'N/A')}")
            break  # Found working method!
    except Exception as e:
        print(f"Error: {e}")

