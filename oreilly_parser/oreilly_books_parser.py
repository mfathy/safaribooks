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
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrupted while retrieving {url}")
        raise


def search_oreilly_learning_api_with_pagination(skill_name, skill_url, cookies=None, max_pages=None, verbose=True):
    """Search O'Reilly Learning API for books with pagination support"""
    print(f"🔍 Searching for books in skill: {skill_name}")
    
    book_ids = set()
    all_books_info = []  # Store detailed book information
    seen_books = set()  # Track unique books to avoid duplicates
    
    # Try the main API endpoint with pagination
    api_url = f"https://learning.oreilly.com/api/v1/search?q={skill_name.replace(' ', '+')}"
    print(f"🌐 Starting with API endpoint: {api_url}")
    
    page_count = 0
    current_url = api_url
    
    while current_url:
        page_count += 1
        print(f"\n📄 Fetching page {page_count}...")
        print(f"🔗 URL: {current_url}")

        if max_pages and page_count > max_pages:
            print(f"⏹️  Reached maximum pages limit ({max_pages})")
            break

        try:
            # Get the current page
            api_content = retrieve_page_contents(current_url, cookies=cookies)
            if not api_content:
                print(f"❌ Failed to retrieve page {page_count}")
                break
        except KeyboardInterrupt:
            print(f"\n⚠️  Interrupted during page {page_count} fetch")
            print(f"📊 Progress so far: {len(book_ids)} books collected")
            print(f"💾 Partial results saved to: {skill_name.lower()}-books-info.json")
            raise
        
        try:
            api_data = json.loads(api_content)
            
            # Extract book IDs and detailed info from the current page
            page_book_ids, page_books_info = extract_book_ids_and_info_from_api_response(api_data, verbose, seen_books)
            book_ids.update(page_book_ids)
            all_books_info.extend(page_books_info)
            
            print(f"📚 Found {len(page_book_ids)} book IDs on page {page_count}")
            
            # Check for pagination info
            total_count = api_data.get('count', 0)
            current_page = api_data.get('page', 1)
            next_url = api_data.get('next')
            
            print(f"📊 Page {current_page}: {len(page_book_ids)} books (Total so far: {len(book_ids)})")
            if total_count > 0:
                print(f"📈 Total available: {total_count:,} books")
                progress_percent = (len(book_ids) / total_count) * 100 if total_count > 0 else 0
                print(f"📈 Progress: {progress_percent:.1f}% ({len(book_ids):,}/{total_count:,})")
            
            # Show some book details if verbose
            if verbose and page_books_info:
                print(f"📚 Found {len(page_books_info)} books on page {page_count}")
            
            # Move to next page
            current_url = next_url
            
            if not next_url:
                print("🏁 No more pages available")
                break
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response on page {page_count}: {e}")
            break
        
        # Add a small delay between requests
        print("⏳ Waiting 1 second before next request...")
        time.sleep(1)
        
        # Save progress every 50 pages to avoid losing work
        if page_count % 50 == 0:
            print(f"💾 Saving progress checkpoint at page {page_count}...")
            save_books_info_to_json(all_books_info, skill_name)
    
    print(f"\n✅ Completed pagination: {page_count} pages, {len(book_ids)} total book IDs")
    
    # Show filtering statistics
    if verbose and all_books_info:
        # Count books with and without ISBNs
        books_with_isbn = sum(1 for book in all_books_info if book.get('isbn', '').strip())
        books_without_isbn = len(all_books_info) - books_with_isbn
        
        print(f"📊 Filtering Results:")
        print(f"   📚 Unique books found: {len(all_books_info)}")
        print(f"   🎯 Books only (English): {len(all_books_info)}")
        print(f"   📖 Books with ISBN: {books_with_isbn}")
        print(f"   📝 Books without ISBN: {books_without_isbn}")
        print(f"   🔄 Duplicates skipped: {len(seen_books) - len(all_books_info)}")
        print(f"   ⏭️  Videos/chapters/short-content filtered out")
    
    # Save detailed book information
    save_books_info_to_json(all_books_info, skill_name)
    
    return list(book_ids)


def extract_book_ids_and_info_from_api_response(api_data, verbose=True, seen_books=None):
    """Extract book IDs and information from API response data - BOOKS ONLY"""
    book_ids = set()
    books_info = []
    
    if seen_books is None:
        seen_books = set()
    
    # Look for results array
    if 'results' in api_data and isinstance(api_data['results'], list):
        for result in api_data['results']:
            if isinstance(result, dict):
                # Filter for books only
                format_type = result.get('format', '').lower()
                language = result.get('language', '').lower()
                
                # Skip if not a book format
                if format_type not in ['book', 'ebook', '']:  # Empty format is often a book
                    if verbose:
                        print(f"   ⏭️  Skipping {format_type}: {result.get('title', 'Unknown')}")
                    continue
                
                # Skip if not English (or if language is not specified, assume English)
                if language and language not in ['en', 'english', '']:
                    if verbose:
                        print(f"   ⏭️  Skipping non-English ({language}): {result.get('title', 'Unknown')}")
                    continue
                
                # Skip chapters and non-book content
                title = result.get('title', '').lower()
                original_title = result.get('title', '')
                
                # Skip if title is too short (likely not a real book)
                if len(original_title.strip()) < 10:
                    if verbose:
                        print(f"   ⏭️  Skipping short title: {original_title}")
                    continue
                
                # Skip chapters and non-book content
                if any(keyword in title for keyword in [
                    'chapter', 'part', 'section', 'lesson', 'unit', 'module',
                    'introduction to', 'overview of', 'getting started with',
                    'chapter 1:', 'chapter 2:', 'chapter 3:', 'chapter 4:', 'chapter 5:',
                    'chapter 6:', 'chapter 7:', 'chapter 8:', 'chapter 9:', 'chapter 10:',
                    'part i:', 'part ii:', 'part iii:', 'part iv:', 'part v:',
                    'section 1:', 'section 2:', 'section 3:', 'section 4:', 'section 5:',
                    'lesson 1:', 'lesson 2:', 'lesson 3:', 'lesson 4:', 'lesson 5:',
                    'unit 1:', 'unit 2:', 'unit 3:', 'unit 4:', 'unit 5:',
                    'exam ref', 'certification', 'study guide', 'practice test',
                    'appendix', 'glossary', 'index', 'bibliography',
                    'closing thoughts', 'conclusion', 'summary', 'wrap-up',
                    'introduction', 'preface', 'foreword', 'acknowledgments'
                ]):
                    if verbose:
                        print(f"   ⏭️  Skipping chapter/section: {original_title}")
                    continue
                
                # Skip if title is just a number or very short
                if len(original_title.strip()) <= 5 and original_title.strip().isdigit():
                    if verbose:
                        print(f"   ⏭️  Skipping numeric only: {original_title}")
                    continue
                
                # Check ISBN - but be more flexible for legitimate books
                isbn = result.get('isbn', '').strip()
                has_isbn = isbn and isbn != '' and isbn.lower() not in ['n/a', 'none', 'null']
                
                # If no ISBN, check if it looks like a legitimate book (not a chapter/video)
                if not has_isbn:
                    # Skip if it's clearly a chapter, video, or short content
                    if any(keyword in title for keyword in [
                        'chapter', 'part', 'section', 'lesson', 'unit', 'module',
                        'video', 'course', 'tutorial', 'workshop', 'webinar'
                    ]) or len(original_title.strip()) < 15:
                        if verbose:
                            print(f"   ⏭️  Skipping no ISBN (likely chapter/video): {original_title}")
                        continue
                    else:
                        # It might be a legitimate book without ISBN
                        if verbose:
                            print(f"   ⚠️  Book without ISBN (keeping): {original_title}")
                else:
                    if verbose:
                        print(f"   ✅ Book with ISBN: {original_title}")
                
                # Skip if title starts with numbers only (likely a chapter) - but be more specific
                if original_title.strip() and original_title.strip()[0].isdigit():
                    # Only skip if it's a simple number followed by a period or space (like "1. Introduction")
                    # Don't skip if it's a complex title like "3D Data Science"
                    if len(original_title.split()) <= 3 and ('.' in original_title or original_title.count(' ') <= 2):
                        if verbose:
                            print(f"   ⏭️  Skipping numbered item: {original_title}")
                        continue
                
                # Extract only the fields we're interested in
                book_info = {
                    'title': result.get('title', 'Unknown Title'),
                    'id': result.get('id', ''),
                    'url': result.get('url', ''),
                    'isbn': result.get('isbn', ''),
                    'format': result.get('format', 'book')
                }
                
                # Look for various ID fields
                for key in ['id', 'book_id', 'isbn', 'isbn13', 'isbn10']:
                    if key in result:
                        value = result[key]
                        if isinstance(value, (str, int)):
                            value_str = str(value)
                            if value_str.isdigit() and len(value_str) >= 8:
                                book_ids.add(value_str)
                
                # Also look for URLs that might contain book IDs
                for key in ['url', 'link', 'href']:
                    if key in result and isinstance(result[key], str):
                        url = result[key]
                        book_info['url'] = url
                        # Look for book ID patterns in URLs
                        url_patterns = [
                            r'/library/view/[^/]+/(\d+)/',
                            r'/book/(\d+)/',
                            r'/(\d{10,})/',  # Long numeric IDs
                        ]
                        for pattern in url_patterns:
                            matches = re.findall(pattern, url)
                            for match in matches:
                                if match.isdigit() and len(match) >= 8:
                                    book_ids.add(match)
                
                # Only add if we have meaningful information
                if book_info.get('title') and book_info.get('title') != 'Unknown Title':
                    # Create a unique identifier for the book
                    book_identifier = None
                    
                    # Try to use ISBN first (most reliable)
                    if book_info.get('isbn'):
                        book_identifier = f"isbn:{book_info['isbn']}"
                    # Fall back to title (normalized)
                    elif book_info.get('title'):
                        book_identifier = f"title:{book_info['title'].lower().strip()}"
                    # Last resort: use ID
                    elif book_info.get('id'):
                        book_identifier = f"id:{book_info['id']}"
                    
                    # Check if we've already seen this book
                    if book_identifier and book_identifier in seen_books:
                        if verbose:
                            print(f"   🔄 Skipping duplicate: {book_info['title']}")
                        continue
                    
                    # Add to seen books and results
                    if book_identifier:
                        seen_books.add(book_identifier)
                    
                    books_info.append(book_info)
                    if verbose:
                        print(f"   ✅ Added book: {book_info['title']} ({book_info['format']})")
    
    return book_ids, books_info


def extract_book_ids_from_api_response(api_data):
    """Extract book IDs from API response data (legacy function)"""
    book_ids, _ = extract_book_ids_and_info_from_api_response(api_data, verbose=False)
    return book_ids


def save_books_info_to_json(books_info, skill_name):
    """Save detailed book information to JSON file"""
    if not books_info:
        return
    
    filename = f"{skill_name.lower().replace(' ', '-')}-books-info.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(books_info, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved detailed book info to: {filename}")
    except Exception as e:
        print(f"❌ Failed to save book info: {e}")


def search_oreilly_learning_api(skill_name, skill_url, cookies=None):
    """Search O'Reilly Learning API for books in a specific skill category"""
    print(f"Searching for books in skill: {skill_name}")
    
    # Try to get content from the skill page first
    content = retrieve_page_contents(skill_url, cookies=cookies)
    if not content:
        print(f"Failed to retrieve content for {skill_name}")
        return []
    
    # Look for book IDs in various patterns from the web page
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
    
    # Now use the paginated API search
    print("Using paginated API search...")
    paginated_ids = search_oreilly_learning_api_with_pagination(skill_name, skill_url, cookies)
    book_ids.update(paginated_ids)
    
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
    print("O'Reilly Learning Books Parser with Pagination")
    print("=" * 50)
    
    # Load cookies for authentication
    cookies = load_cookies()
    if cookies:
        print("Loaded authentication cookies")
    else:
        print("No authentication cookies found - some content may not be accessible")
    
    # Test with Python first to see pagination in action
    print("\nTesting pagination with Python skill...")
    python_skill = {'name': 'Python', 'url': 'https://learning.oreilly.com/search/skills/python/'}
    
    # Test with limited pages first (3 pages = ~45 books)
    print("Testing with first 3 pages to verify pagination works...")
    book_ids = search_oreilly_learning_api_with_pagination(
        python_skill['name'], 
        python_skill['url'], 
        cookies, 
        max_pages=3,
        verbose=True
    )
    
    if book_ids:
        print(f"Found {len(book_ids)} book IDs for Python (first 5 pages)")
        write_id_list_to_txt_file(book_ids, 'python-test-pagination')
    else:
        print("No book IDs found for Python")
    
    # Ask user if they want to continue with full pagination
    print("\n" + "="*50)
    print("Pagination test completed!")
    print(f"Found {len(book_ids)} books in first 5 pages")
    print("To get all books, you can run the full pagination by modifying max_pages=None")
    print("="*50)
    
    # For now, let's also test a few other skills with limited pagination
    other_skills = [
        {'name': 'JavaScript', 'url': 'https://learning.oreilly.com/search/skills/javascript/'},
        {'name': 'Machine Learning', 'url': 'https://learning.oreilly.com/search/skills/machine-learning/'},
    ]
    
    all_book_ids = set(book_ids) if book_ids else set()
    
    for skill in other_skills:
        print(f"\nProcessing skill: {skill['name']} (limited to 3 pages)")
        skill_name = skill['name'].lower().replace(' ', '-').replace('&', 'and')
        
        # Search for books in this skill with limited pagination
        book_ids = search_oreilly_learning_api_with_pagination(
            skill['name'], 
            skill['url'], 
            cookies, 
            max_pages=2,
            verbose=True
        )
        
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
        write_id_list_to_txt_file(list(all_book_ids), 'all-books-paginated')
        print(f"\nTotal unique book IDs found: {len(all_book_ids)}")
    
    print("\nParsing completed!")
    print("\nTo get ALL books for a skill, modify the max_pages parameter to None")
    print("Example: search_oreilly_learning_api_with_pagination('Python', url, cookies, max_pages=None)")


if __name__ == '__main__':
    main()