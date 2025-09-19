#!/usr/bin/env python3
"""
Example script demonstrating how to use the refactored download_book function.

This script shows how to programmatically download books using the new
download_book function instead of the CLI interface.
"""

import os
from safaribooks_refactored import download_book, parse_cred


def main():
    """Example usage of the download_book function."""
    
    # Example 1: Download with existing cookies
    print("Example 1: Download with existing cookies")
    try:
        book_id = "1234567890123"  # Replace with actual book ID
        output_dir = "/tmp/safaribooks_downloads"
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Download book (will use existing cookies.json)
        book_path = download_book(book_id, output_dir)
        print(f"✅ Book downloaded to: {book_path}")
        
    except Exception as e:
        print(f"❌ Error downloading book: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Example 2: Download with credentials
    print("Example 2: Download with credentials")
    try:
        book_id = "1234567890123"  # Replace with actual book ID
        output_dir = "/tmp/safaribooks_downloads"
        
        # Parse credentials (you would get these from user input or config)
        credentials = parse_cred("your_email@example.com:your_password")
        
        if credentials:
            book_path = download_book(book_id, output_dir, credentials)
            print(f"✅ Book downloaded to: {book_path}")
        else:
            print("❌ Invalid credentials format")
            
    except Exception as e:
        print(f"❌ Error downloading book: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Example 3: Batch download multiple books
    print("Example 3: Batch download multiple books")
    book_ids = [
        "1234567890123",
        "1234567890124", 
        "1234567890125"
    ]
    
    output_dir = "/tmp/safaribooks_batch"
    os.makedirs(output_dir, exist_ok=True)
    
    for book_id in book_ids:
        try:
            print(f"Downloading book {book_id}...")
            book_path = download_book(book_id, output_dir)
            print(f"✅ {book_id} downloaded to: {book_path}")
        except Exception as e:
            print(f"❌ Failed to download {book_id}: {e}")


if __name__ == "__main__":
    main()
