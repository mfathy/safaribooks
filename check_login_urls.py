#!/usr/bin/env python3
"""
Check what login URLs are currently working.
"""

import requests
import time

def check_urls():
    """Check various login URLs to see which ones work."""
    print("Checking Safari Books Online Login URLs")
    print("=" * 50)
    
    urls_to_check = [
        ("Safari Base", "https://learning.oreilly.com"),
        ("Safari Login (old)", "https://learning.oreilly.com/login/unified/?next=/home/"),
        ("Safari Login (new)", "https://learning.oreilly.com/login/"),
        ("Safari Login (simple)", "https://learning.oreilly.com/login"),
        ("O'Reilly Login", "https://www.oreilly.com/member/auth/login/"),
        ("O'Reilly Member", "https://www.oreilly.com/member/"),
        ("Safari Profile", "https://learning.oreilly.com/profile/"),
    ]
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
    })
    
    working_urls = []
    
    for name, url in urls_to_check:
        print(f"Testing {name}...")
        try:
            start_time = time.time()
            response = session.get(url, timeout=10, allow_redirects=True)
            response_time = time.time() - start_time
            
            status = "✅" if response.status_code < 400 else "❌"
            print(f"  {status} {name}: {response.status_code} ({response_time:.2f}s)")
            print(f"    Final URL: {response.url}")
            
            if response.status_code < 400:
                working_urls.append((name, url, response.url))
                
            # Check if it's a login page
            if "login" in response.text.lower() or "sign in" in response.text.lower():
                print(f"    🔑 Contains login form")
                
        except requests.exceptions.Timeout:
            print(f"  ⏰ {name}: Timeout")
        except requests.exceptions.ConnectionError as e:
            print(f"  🔌 {name}: Connection Error - {e}")
        except Exception as e:
            print(f"  ❌ {name}: Error - {e}")
    
    print("\n" + "=" * 50)
    print("Working URLs:")
    print("=" * 50)
    
    for name, original_url, final_url in working_urls:
        print(f"✅ {name}")
        print(f"   Original: {original_url}")
        print(f"   Final: {final_url}")
        print()
    
    return working_urls

def main():
    """Main function."""
    working_urls = check_urls()
    
    if working_urls:
        print("🎉 Found working URLs!")
        print("The login system may have changed. Check the working URLs above.")
    else:
        print("❌ No working URLs found.")
        print("Safari Books Online may be down or the URLs have changed significantly.")

if __name__ == "__main__":
    main()
