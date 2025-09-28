#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
O'Reilly Learning Books Parser
Updated to work with current O'Reilly Learning API structure
"""

import requests
import re
import json
import time
import os
from urllib.parse import urljoin, urlparse


def load_cookies():
    """Load cookies from the cookies.json file if it exists"""
    cookies_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cookies.json')
    if os.path.exists(cookies_file):
        try:
            with open(cookies_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("Warning: Could not load cookies from cookies.json")
    return {}


def retrieve_page_contents(url, headers=None, cookies=None):
    """Retrieve page contents with proper error handling and authentication"""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://learning.oreilly.com/',
        }
    
    try:
        session = requests.Session()
        if cookies:
            session.cookies.update(cookies)
        
        r = session.get(url, headers=headers, timeout=30)
        if r.status_code < 400:
            return r.text
        else:
            print(f"URL {url} returned status code: {r.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error retrieving {url}: {e}")
        return None


def search_oreilly_learning_api(skill_name, skill_url, cookies=None):
    """Search O'Reilly Learning API for books in a specific skill category"""
    print(f"Searching for books in skill: {skill_name}")
    
    # Try to get content from the skill page
    content = retrieve_page_contents(skill_url, cookies=cookies)
    if not content:
        print(f"Failed to retrieve content for {skill_name}")
        return []
    
    # Look for book IDs in various patterns
    book_ids = set()
    
    # Pattern 1: Look for library/view URLs
    library_pattern = r'/library/view/[^/]+/(\d+)/'
    library_matches = re.findall(library_pattern, content)
    for match in library_matches:
        if match.isdigit() and len(match) >= 8:
            book_ids.add(match)
    
    # Pattern 2: Look for API responses with book data
    api_pattern = r'"id":\s*(\d+)'
    api_matches = re.findall(api_pattern, content)
    for match in api_matches:
        if match.isdigit() and len(match) >= 8:
            book_ids.add(match)
    
    # Pattern 3: Look for book URLs in JSON data
    json_pattern = r'"url":\s*"[^"]*/(\d+)/'
    json_matches = re.findall(json_pattern, content)
    for match in json_matches:
        if match.isdigit() and len(match) >= 8:
            book_ids.add(match)
    
    # Pattern 4: Look for ISBN patterns
    isbn_pattern = r'"isbn":\s*"(\d+)"'
    isbn_matches = re.findall(isbn_pattern, content)
    for match in isbn_matches:
        if match.isdigit() and len(match) >= 8:
            book_ids.add(match)
    
    # Try to find and call API endpoints directly
    api_endpoints = [
        f"https://api.oreilly.com/api/v1/search?q={skill_name.replace(' ', '+')}",
        f"https://learning.oreilly.com/api/v1/search?q={skill_name.replace(' ', '+')}",
        f"https://api.oreilly.com/api/v1/books?topic={skill_name.lower().replace(' ', '-')}",
    ]
    
    for api_url in api_endpoints:
        print(f"Trying API endpoint: {api_url}")
        api_content = retrieve_page_contents(api_url, cookies=cookies)
        if api_content:
            try:
                api_data = json.loads(api_content)
                # Recursively search for book IDs in the API response
                def find_book_ids(obj):
                    ids = []
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if key in ['id', 'book_id', 'isbn', 'isbn13'] and isinstance(value, (str, int)):
                                if str(value).isdigit() and len(str(value)) >= 8:
                                    ids.append(str(value))
                            elif isinstance(value, (dict, list)):
                                ids.extend(find_book_ids(value))
                    elif isinstance(obj, list):
                        for item in obj:
                            ids.extend(find_book_ids(item))
                    return ids
                
                api_book_ids = find_book_ids(api_data)
                book_ids.update(api_book_ids)
                print(f"Found {len(api_book_ids)} book IDs from API")
            except json.JSONDecodeError:
                print("API response is not valid JSON")
    
    return list(book_ids)


def write_id_list_to_txt_file(id_list, filename):
    """Write book IDs to a text file"""
    if not id_list:
        print(f"No book IDs found for {filename}")
        return
    
    with open(f"{filename}.txt", 'w') as txt_file_handler:
        txt_file_handler.write("\n".join([str(book_id) for book_id in id_list]))
    
    print(f"Wrote {len(id_list)} book IDs to {filename}.txt")


def main():
    """Main function to parse O'Reilly Learning books"""
    print("O'Reilly Learning Books Parser")
    print("=" * 40)
    
    # Load cookies for authentication
    cookies = load_cookies()
    if cookies:
        print("Loaded authentication cookies")
    else:
        print("No authentication cookies found - some content may not be accessible")
    
    # Define skills to search for
    skills = [
        {'name': 'Python', 'url': 'https://learning.oreilly.com/search/skills/python/'},
        {'name': 'JavaScript', 'url': 'https://learning.oreilly.com/search/skills/javascript/'},
        {'name': 'Java', 'url': 'https://learning.oreilly.com/search/skills/java/'},
        {'name': 'Machine Learning', 'url': 'https://learning.oreilly.com/search/skills/machine-learning/'},
        {'name': 'Data Science', 'url': 'https://learning.oreilly.com/search/skills/data-science/'},
        {'name': 'Cloud Computing', 'url': 'https://learning.oreilly.com/search/skills/cloud-computing/'},
        {'name': 'Security', 'url': 'https://learning.oreilly.com/search/skills/security/'},
        {'name': 'DevOps', 'url': 'https://learning.oreilly.com/search/skills/devops/'},
        {'name': 'AWS', 'url': 'https://learning.oreilly.com/search/skills/amazon-web-services-aws/'},
        {'name': 'Docker', 'url': 'https://learning.oreilly.com/search/skills/docker/'},
    ]
    
    print(f"Processing {len(skills)} skills...")
    
    all_book_ids = set()
    
    # Process each skill
    for skill in skills:
        skill_name = skill['name'].lower().replace(' ', '-').replace('&', 'and')
        skill_url = skill['url']
        
        print(f"\nProcessing skill: {skill['name']}")
        print(f"URL: {skill_url}")
        
        # Search for books in this skill
        book_ids = search_oreilly_learning_api(skill['name'], skill_url, cookies)
        
        if book_ids:
            print(f"Found {len(book_ids)} book IDs for {skill['name']}")
            write_id_list_to_txt_file(book_ids, skill_name)
            all_book_ids.update(book_ids)
        else:
            print(f"No book IDs found for {skill['name']}")
        
        # Add a small delay to be respectful to the server
        time.sleep(2)
    
    # Write all unique book IDs to a master file
    if all_book_ids:
        write_id_list_to_txt_file(list(all_book_ids), 'all-books')
        print(f"\nTotal unique book IDs found: {len(all_book_ids)}")
    
    print("\nParsing completed!")


if __name__ == '__main__':
    main()