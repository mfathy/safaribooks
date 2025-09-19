#!/usr/bin/env python3
"""
Debug script that mimics the exact authentication flow from the refactored version.
"""

import requests
import json
import os
import re

# Copy the exact constants from the refactored version
ORLY_BASE_HOST = "oreilly.com"
SAFARI_BASE_HOST = "learning." + ORLY_BASE_HOST
API_ORIGIN_HOST = "api." + ORLY_BASE_HOST

ORLY_BASE_URL = "https://www." + ORLY_BASE_HOST
SAFARI_BASE_URL = "https://" + SAFARI_BASE_HOST
API_ORIGIN_URL = "https://" + API_ORIGIN_HOST
PROFILE_URL = SAFARI_BASE_URL + "/profile/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

COOKIE_FLOAT_MAX_AGE_PATTERN = re.compile(r"Max-Age=(\d+(?:\.\d+)?)")

def handle_cookie_update(set_cookie_headers):
    """Mimic the handle_cookie_update method from the refactored version."""
    for morsel in set_cookie_headers:
        if morsel and "Max-Age" in morsel:
            if COOKIE_FLOAT_MAX_AGE_PATTERN.search(morsel):
                cookie_key, cookie_value = morsel.split(";")[0].split("=")
                print(f"🍪 Updating cookie: {cookie_key}")
                return cookie_key, cookie_value
    return None, None

def requests_provider(session, url, perform_redirect=True, timeout=30):
    """Mimic the requests_provider method from the refactored version."""
    try:
        response = session.get(
            url,
            allow_redirects=perform_redirect,
            timeout=timeout
        )
        
        # Handle cookie updates
        set_cookie_headers = response.raw.headers.getlist("Set-Cookie")
        if set_cookie_headers:
            handle_cookie_update(set_cookie_headers)
        
        return response
        
    except Exception as e:
        print(f"❌ Request error: {e}")
        return None

def check_login(session):
    """Mimic the check_login method from the refactored version."""
    print("🔍 Testing check_login method...")
    
    response = requests_provider(session, PROFILE_URL, perform_redirect=False)
    
    if response is None:
        raise ConnectionError("Unable to reach Safari Books Online. Try again...")
    
    print(f"📊 Response status code: {response.status_code}")
    print(f"📊 Response headers: {dict(response.headers)}")
    
    if response.status_code != 200:
        print(f"❌ Status code {response.status_code} is not 200")
        raise ValueError("Authentication issue: unable to access profile page.")
    elif "user_type\":\"Expired\"" in response.text:
        raise ValueError("Authentication issue: account subscription expired.")
    
    print("✅ Successfully authenticated.")
    return True

def test_refactored_auth():
    """Test authentication exactly like the refactored version."""
    print("🔍 Testing Refactored Authentication Flow")
    print("=" * 50)
    
    # Load cookies
    cookies_file = "cookies.json"
    if not os.path.isfile(cookies_file):
        print("❌ cookies.json not found")
        return
    
    print("✅ cookies.json found")
    
    # Create session exactly like the refactored version
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # Load cookies
    with open(cookies_file, 'r') as f:
        cookies = json.load(f)
    
    session.cookies.update(cookies)
    print(f"📊 Loaded {len(cookies)} cookies into session")
    
    # Test authentication
    try:
        check_login(session)
        print("🎉 Authentication successful!")
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_refactored_auth()
