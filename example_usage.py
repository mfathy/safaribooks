#!/usr/bin/env python3
"""
Example usage of the SessionManager class.

This script demonstrates how to use the SessionManager for authentication
with O'Reilly's Safari Books Online platform.
"""

import logging
from oreilly_scraper.auth import SessionManager, InvalidCookieError, SessionExpiredError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

def main():
    """Demonstrate SessionManager usage."""
    
    try:
        # Initialize SessionManager with default configuration
        print("Initializing SessionManager...")
        session_manager = SessionManager()
        
        # Get an authenticated session
        print("Getting authenticated session...")
        session = session_manager.get_session()
        
        print(f"✅ Successfully created authenticated session!")
        print(f"   - Cookies loaded: {len(session.cookies)} cookies")
        print(f"   - User-Agent: {session.headers.get('User-Agent', 'Not set')}")
        
        # Example: Make a request to test the session
        print("\nTesting session with a lightweight request...")
        try:
            response = session.get('https://learning.oreilly.com/profile/', timeout=10)
            print(f"   - Response status: {response.status_code}")
            print(f"   - Response size: {len(response.content)} bytes")
            
            if response.status_code == 200:
                print("✅ Session is working correctly!")
            else:
                print(f"⚠️  Unexpected response code: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing session: {e}")
        
        # Example: Using as context manager
        print("\nDemonstrating context manager usage...")
        with SessionManager() as ctx_session:
            print(f"   - Context session created with {len(ctx_session.cookies)} cookies")
            # Session will be automatically closed when exiting the context
        
        print("✅ Context manager example completed!")
        
    except InvalidCookieError as e:
        print(f"❌ Cookie Error: {e}")
        print("   Please ensure you have valid cookies in cookies.json")
        print("   You can obtain cookies by:")
        print("   1. Logging into Safari Books Online in your browser")
        print("   2. Using the retrieve_cookies.py script")
        print("   3. Or using the --cred option with safaribooks.py")
        
    except SessionExpiredError as e:
        print(f"❌ Session Expired: {e}")
        print("   Your session has expired. Please:")
        print("   1. Log in again to Safari Books Online")
        print("   2. Update your cookies.json file")
        print("   3. Or use the --cred option to re-authenticate")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        print("   Please check your configuration and try again")

if __name__ == "__main__":
    main()

