#!/usr/bin/env python3
"""
Test script to verify the refactored download_book function works with a real book ID.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add current directory to path to import our module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_download_book():
    """Test the download_book function with a real book ID."""
    
    book_id = "9780136766803"
    print(f"Testing download with book ID: {book_id}")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        try:
            # Import the download function
            from safaribooks_refactored import download_book
            
            print("✅ Successfully imported download_book function")
            
            # Test the download
            print("Starting download...")
            book_path = download_book(book_id, temp_dir)
            
            print(f"✅ Download completed! Book saved to: {book_path}")
            
            # Verify the output structure
            if os.path.exists(book_path):
                print(f"✅ Book directory exists: {book_path}")
                
                # Check for OEBPS structure
                oebps_path = os.path.join(book_path, "OEBPS")
                if os.path.exists(oebps_path):
                    print(f"✅ OEBPS directory exists: {oebps_path}")
                    
                    # Check for Styles and Images directories
                    styles_path = os.path.join(oebps_path, "Styles")
                    images_path = os.path.join(oebps_path, "Images")
                    
                    if os.path.exists(styles_path):
                        css_files = os.listdir(styles_path)
                        print(f"✅ Styles directory exists with {len(css_files)} CSS files")
                    else:
                        print("⚠️  Styles directory not found")
                    
                    if os.path.exists(images_path):
                        image_files = os.listdir(images_path)
                        print(f"✅ Images directory exists with {len(image_files)} image files")
                    else:
                        print("⚠️  Images directory not found")
                    
                    # Check for XHTML files
                    xhtml_files = [f for f in os.listdir(oebps_path) if f.endswith('.xhtml')]
                    print(f"✅ Found {len(xhtml_files)} XHTML chapter files")
                    
                    if xhtml_files:
                        print("Sample XHTML files:")
                        for f in xhtml_files[:3]:  # Show first 3 files
                            print(f"  - {f}")
                        if len(xhtml_files) > 3:
                            print(f"  ... and {len(xhtml_files) - 3} more")
                    
                else:
                    print("❌ OEBPS directory not found")
                    return False
                
                # List directory contents
                print(f"\nDirectory structure:")
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
            else:
                print(f"❌ Book directory not found: {book_path}")
                return False
                
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("Make sure safaribooks_refactored.py is in the current directory")
            return False
        except Exception as e:
            print(f"❌ Download failed: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main test function."""
    print("=" * 60)
    print("Testing SafariBooks Refactored Download Function")
    print("=" * 60)
    
    success = test_download_book()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 TEST PASSED! The refactored download function works correctly.")
        print("✅ Ready to commit changes.")
    else:
        print("❌ TEST FAILED! Please check the issues above.")
        print("❌ Do not commit until issues are resolved.")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
