#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Cleanup Script
Cleans up the messy file structure and organizes everything properly
"""

import os
import shutil
from pathlib import Path


def cleanup_project():
    """Clean up the project directory"""
    print("🧹 Cleaning up O'Reilly Books project...")
    
    # Check if temp_discovery exists and has files
    temp_dir = Path("temp_discovery")
    if temp_dir.exists():
        temp_files = list(temp_dir.glob("*-books-info.json"))
        print(f"📁 Found {len(temp_files)} files in temp_discovery/")
        
        # Move them to the correct location
        book_ids_dir = Path("book_ids")
        book_ids_dir.mkdir(exist_ok=True)
        
        moved_count = 0
        for temp_file in temp_files:
            # Extract skill name from filename
            skill_name = temp_file.stem.replace('-books-info', '').replace('-', ' ')
            
            # Create proper filename
            sanitized_name = skill_name.replace(' ', '_').replace('&', 'and').replace('(', '').replace(')', '').replace(',', '')
            target_file = book_ids_dir / f"{sanitized_name}_books.json"
            
            # Read and reformat the file
            try:
                import json
                with open(temp_file, 'r', encoding='utf-8') as f:
                    books_info = json.load(f)
                
                # Create properly formatted data
                skill_data = {
                    'skill_name': skill_name,
                    'discovery_timestamp': os.path.getmtime(temp_file),
                    'total_books': len(books_info),
                    'books': books_info
                }
                
                # Save to correct location
                with open(target_file, 'w', encoding='utf-8') as f:
                    json.dump(skill_data, f, indent=2, ensure_ascii=False)
                
                moved_count += 1
                print(f"  ✅ Moved: {skill_name} ({len(books_info)} books)")
                
            except Exception as e:
                print(f"  ❌ Error processing {temp_file}: {e}")
        
        print(f"📚 Successfully processed {moved_count} skill files")
        
        # Remove temp directory
        shutil.rmtree(temp_dir)
        print("🗑️  Removed temp_discovery/ directory")
    
    # Check for any remaining JSON files in root
    root_json_files = list(Path(".").glob("*-books-info.json"))
    if root_json_files:
        print(f"⚠️  Found {len(root_json_files)} JSON files still in root directory")
        
        # Create temp directory and move them
        temp_dir = Path("temp_discovery")
        temp_dir.mkdir(exist_ok=True)
        
        for json_file in root_json_files:
            shutil.move(str(json_file), str(temp_dir / json_file.name))
        
        print(f"📁 Moved remaining files to {temp_dir}/")
        print("💡 Run this script again to process them properly")
        return False
    
    # Clean up other temporary files
    temp_files = [
        "discovery_progress.json",
        "download_progress.json", 
        "discovery_results.json",
        "download_results.json",
        "discovery_summary.txt",
        "book_id_discovery.log",
        "book_downloader.log",
        "skill_downloader.log"
    ]
    
    removed_files = 0
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            removed_files += 1
            print(f"🗑️  Removed: {temp_file}")
    
    if removed_files > 0:
        print(f"🧹 Cleaned up {removed_files} temporary files")
    
    # Check final structure
    print("\n📊 Final project structure:")
    
    if Path("book_ids").exists():
        skill_files = list(Path("book_ids").glob("*_books.json"))
        print(f"📚 Book IDs: {len(skill_files)} skill files in book_ids/")
    
    if Path("books_by_skills").exists():
        skill_dirs = [d for d in Path("books_by_skills").iterdir() if d.is_dir()]
        print(f"📖 Downloads: {len(skill_dirs)} skill folders in books_by_skills/")
    
    print("\n✅ Project cleanup completed!")
    return True


def main():
    """Main cleanup function"""
    print("🎯 O'Reilly Books Project Cleanup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("my_favorite_skills.txt"):
        print("❌ Error: Not in the oreilly-books directory")
        print("Please run this script from the project root directory")
        return
    
    success = cleanup_project()
    
    if success:
        print("\n🎉 Project is now clean and organized!")
        print("\nNext steps:")
        print("1. Run discovery: python3 discover_book_ids.py")
        print("2. Run download: python3 download_books.py")
        print("3. Or use master coordinator: python3 oreilly_automation.py")
    else:
        print("\n⚠️  Some files still need processing.")
        print("Run this script again to complete the cleanup.")


if __name__ == "__main__":
    main()

