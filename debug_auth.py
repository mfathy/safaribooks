#!/usr/bin/env python3
"""
Comprehensive authentication debugging script for SafariBooks.

This script consolidates all authentication debugging functionality:
- Test authentication with cookies
- Check login URLs
- Debug refactored authentication flow
- Validate session management
"""

import requests
import json
import os
import sys
import time
from urllib.parse import urljoin

# Constants
ORLY_BASE_HOST = "oreilly.com"
SAFARI_BASE_HOST = "learning." + ORLY_BASE_HOST
API_ORIGIN_HOST = "api." + ORLY_BASE_HOST

ORLY_BASE_URL = "https://www." + ORLY_BASE_HOST
SAFARI_BASE_URL = "https://" + SAFARI_BASE_HOST
API_ORIGIN_URL = "https://" + API_ORIGIN_HOST
PROFILE_URL = SAFARI_BASE_URL + "/profile/"

def load_cookies():
    """Load cookies from cookies.json file."""
    cookies_file = "cookies.json"
    if not os.path.isfile(cookies_file):
        print("❌ cookies.json not found")
        return None
    
    try:
        with open(cookies_file, 'r') as f:
            cookies_data = json.load(f)
        print(f"✅ Loaded {len(cookies_data)} cookies from {cookies_file}")
        return cookies_data
    except Exception as e:
        print(f"❌ Error loading cookies: {e}")
        return None

def test_cookie_authentication():
    """Test authentication using cookies."""
    print("\n🔍 Testing Cookie Authentication")
    print("=" * 50)
    
    cookies_data = load_cookies()
    if not cookies_data:
        return False
    
    session = requests.Session()
    session.cookies.update(cookies_data)
    
    # Test profile access
    try:
        print(f"Testing profile access: {PROFILE_URL}")
        response = session.get(PROFILE_URL, allow_redirects=True, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            if "profile" in response.url.lower() or "dashboard" in response.url.lower():
                print("✅ Authentication successful - profile accessible")
                return True
            else:
                print("⚠️  Got 200 but redirected away from profile")
                print(f"Final URL: {response.url}")
                return False
        else:
            print(f"❌ Authentication failed - status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing authentication: {e}")
        return False

def check_login_urls():
    """Check what login URLs are currently working."""
    print("\n🌐 Checking Login URLs")
    print("=" * 50)
    
    urls_to_check = [
        ("Safari Base", SAFARI_BASE_URL),
        ("Safari Login", SAFARI_BASE_URL + "/login/"),
        ("O'Reilly Login", ORLY_BASE_URL + "/member/auth/login/"),
        ("O'Reilly Member", ORLY_BASE_URL + "/member/"),
        ("API Origin", API_ORIGIN_URL),
    ]
    
    session = requests.Session()
    
    for name, url in urls_to_check:
        try:
            print(f"Checking {name}: {url}")
            response = session.get(url, timeout=10)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                print("  ✅ Accessible")
            elif response.status_code == 302:
                print(f"  🔄 Redirect to: {response.headers.get('Location', 'Unknown')}")
            else:
                print(f"  ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        time.sleep(1)  # Be nice to the server

def test_api_endpoints():
    """Test API endpoints for authentication."""
    print("\n🔌 Testing API Endpoints")
    print("=" * 50)
    
    cookies_data = load_cookies()
    if not cookies_data:
        return
    
    session = requests.Session()
    session.cookies.update(cookies_data)
    
    # Test API endpoints
    api_endpoints = [
        ("Profile API", SAFARI_BASE_URL + "/api/v1/profile/"),
        ("User API", SAFARI_BASE_URL + "/api/v1/user/"),
        ("Books API", API_ORIGIN_URL + "/v1/books/"),
    ]
    
    for name, url in api_endpoints:
        try:
            print(f"Testing {name}: {url}")
            response = session.get(url, timeout=10)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  ✅ JSON response received")
                    if isinstance(data, dict) and len(data) > 0:
                        print(f"  📊 Response keys: {list(data.keys())[:5]}")
                except:
                    print(f"  ⚠️  Non-JSON response")
            elif response.status_code == 401:
                print(f"  ❌ Unauthorized - cookies may be expired")
            elif response.status_code == 403:
                print(f"  ❌ Forbidden - insufficient permissions")
            else:
                print(f"  ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        time.sleep(1)

def debug_refactored_flow():
    """Debug the exact authentication flow from the refactored version."""
    print("\n🔧 Debugging Refactored Authentication Flow")
    print("=" * 50)
    
    cookies_data = load_cookies()
    if not cookies_data:
        return
    
    session = requests.Session()
    session.cookies.update(cookies_data)
    
    # Mimic the exact flow from SafariBooksDownloader.check_login
    try:
        print("Step 1: Testing profile access with allow_redirects=True")
        response = session.get(PROFILE_URL, allow_redirects=True, timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Final URL: {response.url}")
        
        if response.status_code == 200:
            if "profile" in response.url.lower() or "dashboard" in response.url.lower():
                print("  ✅ Profile accessible - authentication working")
            else:
                print("  ⚠️  Redirected away from profile")
        else:
            print(f"  ❌ Profile access failed")
            
    except Exception as e:
        print(f"  ❌ Error in refactored flow: {e}")

def main():
    """Main debugging function."""
    print("🔍 SafariBooks Authentication Debugger")
    print("=" * 60)
    
    # Run all tests
    test_cookie_authentication()
    check_login_urls()
    test_api_endpoints()
    debug_refactored_flow()
    
    print("\n📋 Summary")
    print("=" * 50)
    print("If authentication is failing:")
    print("1. Check if cookies.json exists and is valid")
    print("2. Try getting fresh cookies from browser")
    print("3. Ensure you're logged into learning.oreilly.com")
    print("4. Check COOKIE_SETUP.md for manual extraction instructions")

if __name__ == "__main__":
    main()