#!/usr/bin/env python3
"""
Debug script to test authentication in the refactored version.
"""

import requests
import json
import os

def test_authentication():
    """Test authentication step by step."""
    print("🔍 Debugging Authentication")
    print("=" * 50)
    
    # Load cookies
    cookies_file = "cookies.json"
    if not os.path.isfile(cookies_file):
        print("❌ cookies.json not found")
        return
    
    print("✅ cookies.json found")
    
    with open(cookies_file, 'r') as f:
        cookies = json.load(f)
    
    print(f"📊 Loaded {len(cookies)} cookies")
    
    # Create session
    session = requests.Session()
    session.cookies.update(cookies)
    
    # Test profile page access
    profile_url = "https://learning.oreilly.com/profile/"
    
    print(f"🌐 Testing profile page: {profile_url}")
    
    try:
        # Test with redirect=False (like the refactored code)
        response = session.get(profile_url, allow_redirects=False, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 Response Length: {len(response.text)}")
        print(f"📊 Headers: {dict(response.headers)}")
        
        # Check response content
        if response.status_code == 200:
            print("✅ Status code is 200")
            
            # Check for user_type
            if 'user_type' in response.text:
                print("✅ Found 'user_type' in response")
                
                # Check for expired
                if 'user_type\":\"Expired\"' in response.text:
                    print("❌ Found 'Expired' user type")
                else:
                    print("✅ No 'Expired' user type found")
            else:
                print("❌ 'user_type' not found in response")
                
            # Check for profile content
            if 'profile' in response.text.lower():
                print("✅ Found 'profile' in response")
            else:
                print("❌ 'profile' not found in response")
                
        else:
            print(f"❌ Status code is {response.status_code}, expected 200")
            
        # Show first 200 characters of response
        print(f"📄 Response preview: {response.text[:200]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_authentication()
