#!/usr/bin/env python3
"""
Test script to help with authentication for Oreilly.
"""

import os
import sys
import getpass
from oreilly import download_book, parse_cred

def test_authentication():
    """Test authentication with user input."""
    print("Oreilly Authentication Test")
    print("=" * 40)
    
    # Get credentials from user
    email = input("Enter your Safari Books Online email: ")
    password = getpass.getpass("Enter your password: ")
    
    credentials = (email, password)
    
    print(f"\nTesting authentication with email: {email}")
    print("This will attempt to log in and download book 9780136766803...")
    
    try:
        # Create a test directory
        test_dir = "/tmp/safaribooks_test"
        os.makedirs(test_dir, exist_ok=True)
        
        # Test download
        book_path = download_book("9780136766803", test_dir, credentials)
        
        print(f"\n✅ SUCCESS! Book downloaded to: {book_path}")
        
        # List downloaded files
        if os.path.exists(book_path):
            print(f"\nDownloaded files:")
            for root, dirs, files in os.walk(book_path):
                level = root.replace(book_path, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files[:5]:  # Show first 5 files
                    print(f"{subindent}{file}")
                if len(files) > 5:
                    print(f"{subindent}... and {len(files) - 5} more files")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
        if "Authentication issue" in str(e):
            print("\nPossible solutions:")
            print("1. Check your email and password")
            print("2. Make sure your Safari Books Online subscription is active")
            print("3. Try logging into Safari Books Online in your browser first")
        
        return False

def main():
    """Main function."""
    print("This script will test authentication and download a book.")
    print("Make sure you have a valid Safari Books Online account.\n")
    
    try:
        success = test_authentication()
        
        if success:
            print("\n🎉 Authentication test passed!")
            print("Your cookies have been updated in cookies.json")
            print("You can now use the regular commands without --login or --cred")
        else:
            print("\n❌ Authentication test failed.")
            print("Please check your credentials and try again.")
            
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    main()
