#!/usr/bin/env python3
"""
Interactive Safari Books Online Login Script
Opens Chrome, waits for user to login, then extracts and saves cookies.
"""

import json
import os
import sqlite3
import shutil
import time
import subprocess
import platform
import webbrowser
from pathlib import Path

class InteractiveLogin:
    """Interactive login manager for Safari Books Online."""
    
    def __init__(self):
        self.system = platform.system()
        self.chrome_paths = self._get_chrome_paths()
        self.cookies_file = "cookies.json"
        self.profile_url = "https://learning.oreilly.com/profile/"
    
    def _get_chrome_paths(self):
        """Get Chrome cookie database paths for different operating systems."""
        if self.system == "Darwin":  # macOS
            return [
                os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Cookies"),
                os.path.expanduser("~/Library/Application Support/Google/Chrome/Profile 1/Cookies"),
            ]
        elif self.system == "Linux":
            return [
                os.path.expanduser("~/.config/google-chrome/Default/Cookies"),
                os.path.expanduser("~/.config/google-chrome/Profile 1/Cookies"),
            ]
        elif self.system == "Windows":
            return [
                os.path.expanduser("~/AppData/Local/Google/Chrome/User Data/Default/Cookies"),
                os.path.expanduser("~/AppData/Local/Google/Chrome/User Data/Profile 1/Cookies"),
            ]
        else:
            return []
    
    def find_chrome_cookies_db(self):
        """Find the Chrome cookies database."""
        for path in self.chrome_paths:
            if os.path.exists(path):
                return path
        return None
    
    def open_login_page(self):
        """Open Safari Books Online login page in Chrome."""
        print("🌐 Opening Safari Books Online login page...")
        
        login_url = "https://learning.oreilly.com/login/"
        
        try:
            # Try to open in Chrome specifically
            if self.system == "Darwin":  # macOS
                subprocess.run([
                    "open", "-a", "Google Chrome", login_url
                ], check=True)
            elif self.system == "Linux":
                subprocess.run([
                    "google-chrome", login_url
                ], check=True)
            elif self.system == "Windows":
                subprocess.run([
                    "start", "chrome", login_url
                ], check=True, shell=True)
            else:
                # Fallback to default browser
                webbrowser.open(login_url)
                
            print("✅ Chrome opened with login page")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  Could not open Chrome specifically, trying default browser...")
            try:
                webbrowser.open(login_url)
                print("✅ Default browser opened with login page")
                return True
            except Exception as e:
                print(f"❌ Could not open browser: {e}")
                return False
    
    def wait_for_login(self):
        """Wait for user to complete login and navigate to profile page."""
        print("\n" + "="*60)
        print("🔐 LOGIN INSTRUCTIONS")
        print("="*60)
        print("1. Complete the login process in the browser")
        print("2. Navigate to your profile page:")
        print(f"   {self.profile_url}")
        print("3. Make sure you can see your profile information")
        print("4. Come back here and press Enter when ready")
        print("="*60)
        
        input("\nPress Enter when you've completed login and are on the profile page...")
        print("✅ Proceeding to extract cookies...")
    
    def extract_cookies_from_browser(self):
        """Extract cookies from the browser using JavaScript."""
        print("🍪 Extracting cookies from browser...")
        
        # Create a temporary HTML file with JavaScript to extract cookies
        js_code = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cookie Extractor</title>
        </head>
        <body>
            <h1>Cookie Extractor</h1>
            <p>This page will extract your Safari Books Online cookies.</p>
            <button onclick="extractCookies()">Extract Cookies</button>
            <div id="result"></div>
            
            <script>
            function extractCookies() {
                const cookies = document.cookie.split(';').reduce((acc, cookie) => {
                    const [name, value] = cookie.trim().split('=');
                    if (name && value) {
                        acc[name] = value;
                    }
                    return acc;
                }, {});
                
                const jsonCookies = JSON.stringify(cookies, null, 2);
                document.getElementById('result').innerHTML = '<pre>' + jsonCookies + '</pre>';
                
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(jsonCookies).then(() => {
                        alert('✅ Cookies copied to clipboard!');
                    });
                }
                
                return cookies;
            }
            </script>
        </body>
        </html>
        """
        
        temp_html = "/tmp/cookie_extractor.html"
        with open(temp_html, 'w') as f:
            f.write(js_code)
        
        print(f"📄 Created temporary cookie extractor: {temp_html}")
        print("Please open this file in your browser and click 'Extract Cookies'")
        
        try:
            if self.system == "Darwin":  # macOS
                subprocess.run(["open", temp_html], check=True)
            elif self.system == "Linux":
                subprocess.run(["xdg-open", temp_html], check=True)
            elif self.system == "Windows":
                subprocess.run(["start", temp_html], check=True, shell=True)
            else:
                webbrowser.open(f"file://{temp_html}")
        except Exception as e:
            print(f"⚠️  Could not open extractor automatically: {e}")
            print(f"Please manually open: {temp_html}")
        
        print("\nAfter extracting cookies, paste the JSON content here:")
        print("(Press Ctrl+D when done, or type 'done' on a new line)")
        
        lines = []
        try:
            while True:
                line = input()
                if line.strip().lower() == 'done':
                    break
                lines.append(line)
        except EOFError:
            pass
        
        if not lines:
            print("❌ No cookies provided")
            return None
        
        try:
            cookies_json = '\n'.join(lines)
            cookies = json.loads(cookies_json)
            return cookies
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON format: {e}")
            return None
    
    def extract_cookies_from_chrome_db(self):
        """Extract cookies from Chrome database (fallback method)."""
        print("🔍 Trying to extract cookies from Chrome database...")
        
        cookie_db = self.find_chrome_cookies_db()
        if not cookie_db:
            print("❌ Chrome cookies database not found")
            return None
        
        try:
            # Create a temporary copy since the database might be locked
            temp_db = "/tmp/chrome_cookies_temp.db"
            shutil.copy2(cookie_db, temp_db)
            
            # Connect to the database
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Check table structure
            cursor.execute("PRAGMA table_info(cookies)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Build query based on available columns
            if 'host_key' in columns:
                query = """
                SELECT name, value, host_key
                FROM cookies 
                WHERE host_key LIKE '%oreilly.com%' OR host_key LIKE '%learning.oreilly.com%'
                ORDER BY name
                """
            else:
                query = """
                SELECT name, value, domain
                FROM cookies 
                WHERE domain LIKE '%oreilly.com%' OR domain LIKE '%learning.oreilly.com%'
                ORDER BY name
                """
            
            cursor.execute(query)
            cookies = {}
            
            for row in cursor.fetchall():
                name, value, domain = row
                if value:  # Only include cookies with values
                    cookies[name] = value
            
            conn.close()
            os.remove(temp_db)
            
            return cookies if cookies else None
            
        except Exception as e:
            print(f"❌ Error extracting from Chrome database: {e}")
            return None
    
    def save_cookies(self, cookies):
        """Save cookies to JSON file."""
        if not cookies:
            print("❌ No cookies to save")
            return False
        
        try:
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            
            print(f"✅ Cookies saved to {self.cookies_file}")
            print(f"Found {len(cookies)} cookies:")
            for name, value in cookies.items():
                print(f"  - {name}: {value[:20]}{'...' if len(value) > 20 else ''}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving cookies: {e}")
            return False
    
    def test_cookies(self):
        """Test if the extracted cookies work."""
        print("\n🧪 Testing extracted cookies...")
        
        try:
            # Try to import and test the downloader
            import requests
            
            session = requests.Session()
            session.cookies.update(json.load(open(self.cookies_file)))
            
            # Test profile access
            response = session.get(self.profile_url, timeout=10)
            
            if response.status_code == 200 and "profile" in response.text.lower():
                print("✅ Cookies are working! Profile page accessible.")
                return True
            else:
                print(f"⚠️  Cookies might be expired or invalid (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"❌ Error testing cookies: {e}")
            return False
    
    def run(self):
        """Run the interactive login process."""
        print("🚀 Safari Books Online Interactive Login")
        print("="*60)
        print("This script will help you login and extract cookies automatically.")
        print()
        
        # Step 1: Open login page
        if not self.open_login_page():
            print("❌ Could not open browser. Please open https://learning.oreilly.com/login/ manually.")
            return False
        
        # Step 2: Wait for user to login
        self.wait_for_login()
        
        # Step 3: Extract cookies
        print("\n🍪 Extracting cookies...")
        
        # Try browser method first
        cookies = self.extract_cookies_from_browser()
        
        # Fallback to Chrome database method
        if not cookies:
            print("\n🔄 Trying alternative extraction method...")
            cookies = self.extract_cookies_from_chrome_db()
        
        if not cookies:
            print("❌ Could not extract cookies. Please try manual extraction.")
            return False
        
        # Step 4: Save cookies
        if not self.save_cookies(cookies):
            return False
        
        # Step 5: Test cookies
        if self.test_cookies():
            print("\n🎉 Login successful! You can now use the Safari Books downloader:")
            print("   python3 safaribooks.py 9780136766803")
            print("   python3 safaribooks_refactored.py 9780136766803")
            return True
        else:
            print("\n⚠️  Cookies extracted but may not be working properly.")
            print("You can still try using the downloader, or extract cookies again.")
            return True

def main():
    """Main function."""
    login_manager = InteractiveLogin()
    success = login_manager.run()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
