#!/usr/bin/env python3
"""
Comprehensive examples for SafariBooks usage.

This script consolidates all example functionality:
- Basic download examples
- SessionManager usage
- Authentication examples
- Error handling examples
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def example_basic_download():
    """Example 1: Basic book download using the refactored function."""
    print("📚 Example 1: Basic Book Download")
    print("=" * 50)
    
    try:
        from safaribooks_refactored import download_book
        
        # Example book ID (replace with actual book ID)
        book_id = "9780136766803"  # Techniques of Visual Persuasion
        output_dir = "Books"
        
        print(f"Downloading book: {book_id}")
        print(f"Output directory: {output_dir}")
        
        # Download the book
        book_path = download_book(book_id, output_dir)
        print(f"✅ Book downloaded successfully to: {book_path}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure safaribooks_refactored.py is in the same directory")
    except Exception as e:
        print(f"❌ Download failed: {e}")

def example_session_manager():
    """Example 2: Using SessionManager for authentication."""
    print("\n🔐 Example 2: SessionManager Usage")
    print("=" * 50)
    
    try:
        from oreilly_scraper.auth import SessionManager, InvalidCookieError, SessionExpiredError
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        print("Creating SessionManager instance...")
        session_manager = SessionManager()
        
        print("Getting authenticated session...")
        session = session_manager.get_session()
        
        print("Testing session with a simple request...")
        response = session.get("https://learning.oreilly.com/profile/")
        
        if response.status_code == 200:
            print("✅ Session is valid and working")
        else:
            print(f"⚠️  Session returned status: {response.status_code}")
            
    except InvalidCookieError as e:
        print(f"❌ Invalid cookie error: {e}")
        print("Please check your cookies.json file")
    except SessionExpiredError as e:
        print(f"❌ Session expired: {e}")
        print("Please get fresh cookies from your browser")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure oreilly_scraper module is properly installed")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def example_error_handling():
    """Example 3: Proper error handling for downloads."""
    print("\n⚠️  Example 3: Error Handling")
    print("=" * 50)
    
    try:
        from safaribooks_refactored import download_book
        
        # Test with invalid book ID
        invalid_book_id = "0000000000000"
        output_dir = "Books"
        
        print(f"Testing with invalid book ID: {invalid_book_id}")
        
        try:
            book_path = download_book(invalid_book_id, output_dir)
            print(f"Unexpected success: {book_path}")
        except Exception as e:
            print(f"✅ Expected error caught: {type(e).__name__}: {e}")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")

def example_batch_download():
    """Example 4: Batch download multiple books."""
    print("\n📦 Example 4: Batch Download")
    print("=" * 50)
    
    try:
        from safaribooks_refactored import download_book
        
        # List of book IDs to download
        book_ids = [
            "9780136766803",  # Techniques of Visual Persuasion
            # Add more book IDs here
        ]
        
        output_dir = "Books"
        successful_downloads = []
        failed_downloads = []
        
        for book_id in book_ids:
            print(f"\nDownloading book: {book_id}")
            try:
                book_path = download_book(book_id, output_dir)
                successful_downloads.append((book_id, book_path))
                print(f"✅ Success: {book_path}")
            except Exception as e:
                failed_downloads.append((book_id, str(e)))
                print(f"❌ Failed: {e}")
        
        # Summary
        print(f"\n📊 Download Summary:")
        print(f"  Successful: {len(successful_downloads)}")
        print(f"  Failed: {len(failed_downloads)}")
        
        if failed_downloads:
            print("\n❌ Failed downloads:")
            for book_id, error in failed_downloads:
                print(f"  {book_id}: {error}")
                
    except ImportError as e:
        print(f"❌ Import error: {e}")

def example_custom_output():
    """Example 5: Custom output directory and organization."""
    print("\n📁 Example 5: Custom Output Organization")
    print("=" * 50)
    
    try:
        from safaribooks_refactored import download_book
        
        # Create custom output structure
        base_output = "MyLibrary"
        book_id = "9780136766803"
        
        # Create organized directory structure
        custom_output = os.path.join(base_output, "Programming", "Visual_Design")
        os.makedirs(custom_output, exist_ok=True)
        
        print(f"Custom output directory: {custom_output}")
        
        book_path = download_book(book_id, custom_output)
        print(f"✅ Book downloaded to custom location: {book_path}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Run all examples."""
    print("🚀 SafariBooks Usage Examples")
    print("=" * 60)
    
    # Check if required files exist
    if not os.path.exists("safaribooks_refactored.py"):
        print("❌ safaribooks_refactored.py not found in current directory")
        return
    
    if not os.path.exists("cookies.json"):
        print("⚠️  cookies.json not found - authentication may fail")
        print("Please follow COOKIE_SETUP.md instructions to set up cookies")
    
    # Run examples
    example_basic_download()
    example_session_manager()
    example_error_handling()
    example_batch_download()
    example_custom_output()
    
    print("\n🎉 Examples completed!")
    print("\nFor more information:")
    print("- Check README.md for setup instructions")
    print("- Check COOKIE_SETUP.md for authentication setup")
    print("- Check METADATA_IMPROVEMENTS.md for metadata features")

if __name__ == "__main__":
    main()
