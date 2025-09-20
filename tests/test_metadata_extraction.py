#!/usr/bin/env python3
"""
Test script for metadata extraction functionality.
"""

import os
import json
import tempfile
from oreilly import OreillyDownloader

def test_metadata_extraction():
    """Test the metadata extraction functionality."""
    print("🧪 Testing Metadata Extraction")
    print("=" * 50)
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        # Initialize downloader
        downloader = OreillyDownloader()
        
        # Test book ID (use a known book ID)
        test_book_id = "9780136766803"
        
        try:
            # Test metadata extraction (without full download)
            print(f"📖 Testing metadata extraction for book: {test_book_id}")
            
            # Create a mock session for testing
            import requests
            session = requests.Session()
            
            # Test the extract_metadata method
            metadata = downloader.extract_metadata(test_book_id, session, temp_dir)
            
            print("✅ Metadata extraction completed!")
            print(f"📊 Extracted metadata:")
            print(f"   Title: {metadata.get('title', 'N/A')}")
            print(f"   Authors: {', '.join(metadata.get('authors', []))}")
            print(f"   Publisher: {metadata.get('publisher', 'N/A')}")
            print(f"   ISBN: {metadata.get('isbn', 'N/A')}")
            print(f"   Release Date: {metadata.get('release_date', 'N/A')}")
            print(f"   Cover URL: {metadata.get('cover_url', 'N/A')}")
            print(f"   Cover Filename: {metadata.get('cover_filename', 'N/A')}")
            
            # Check if metadata.json was created
            metadata_file = os.path.join(temp_dir, "metadata.json")
            if os.path.exists(metadata_file):
                print(f"✅ metadata.json created: {metadata_file}")
                
                # Load and display the JSON content
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    saved_metadata = json.load(f)
                
                print(f"📄 JSON file contains {len(saved_metadata)} fields")
                print("🔍 Sample fields:")
                for key, value in list(saved_metadata.items())[:5]:
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"   {key}: {value}")
            else:
                print("❌ metadata.json was not created")
            
            # Test load_metadata method
            print("\n🔄 Testing load_metadata method...")
            loaded_metadata = downloader.load_metadata(temp_dir)
            print(f"✅ Loaded metadata with {len(loaded_metadata)} fields")
            
            # Verify metadata structure
            required_fields = [
                'book_id', 'title', 'authors', 'publisher', 'isbn',
                'description', 'subjects', 'rights', 'release_date',
                'web_url', 'cover_url', 'cover_filename'
            ]
            
            missing_fields = [field for field in required_fields if field not in loaded_metadata]
            if missing_fields:
                print(f"⚠️  Missing fields: {missing_fields}")
            else:
                print("✅ All required fields present")
            
        except Exception as e:
            print(f"❌ Error during metadata extraction: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n🎉 Metadata extraction test completed!")

if __name__ == "__main__":
    test_metadata_extraction()
