#!/usr/bin/env python3
"""
Quick Download Script - Simplified interface for the two-step download process
"""

import sys
import os
import subprocess

def run_command(cmd, show_output=True):
    """Run a command and return the result"""
    try:
        if show_output:
            # Show live output for better progress tracking
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0, "", ""
        else:
            # Capture output (for quick checks)
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    """Interactive quick download interface"""
    print("🚀 O'Reilly Books Quick Downloader (Two-Step Workflow)")
    print("=" * 60)
    
    # Check if cookies.json exists
    if not os.path.exists('cookies.json'):
        print("❌ Error: cookies.json not found!")
        print("Please set up your O'Reilly authentication first.")
        print("See COOKIE_SETUP.md for instructions.")
        return
    
    print("✅ Authentication cookies found")
    
    # Check if book IDs are discovered
    book_ids_exist = os.path.exists('book_ids') and os.listdir('book_ids')
    
    print("\n📋 Workflow:")
    print("  Step 1: Discover book IDs for skills (discover_book_ids.py)")
    print("  Step 2: Download books from discovered IDs (download_books.py)")
    print("\n💡 Note: If you have a single JSON file with all books, you can skip Step 1")
    
    # Ask which JSON format to use first (to determine if discovery is needed)
    print("\n" + "=" * 60)
    print("Select JSON format:")
    print("=" * 60)
    print("1. Current format (skill-based JSON files from book_ids/ directory)")
    print("2. New format (single JSON file with all books)")
    
    format_choice = input("\nEnter your choice (1-2): ").strip()
    
    json_file_path = None
    if format_choice == "2":
        json_file_path = input("\nEnter path to JSON file (e.g., oreilly-books-2026-01-25.json): ").strip()
        if not json_file_path:
            print("❌ No JSON file path entered")
            return
        if not os.path.exists(json_file_path):
            print(f"❌ JSON file not found: {json_file_path}")
            return
        print(f"✅ Using JSON file: {json_file_path}")
        # Skip discovery if using new format
        book_ids_exist = True  # Set to True to skip discovery prompts
    elif format_choice != "1":
        print("❌ Invalid choice")
        return
    
    # Only prompt for discovery if using current format and book_ids don't exist
    if not book_ids_exist:
        print("\n⚠️  Book IDs not discovered yet. You need to run Step 1 first.")
        print("\nSelect discovery option:")
        print("1. Discover all skills from my_favorite_skills.txt")
        print("2. Discover specific skills")
        print("3. Skip discovery (exit)")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            cmd = "python3 discover_book_ids.py"
        elif choice == "2":
            skills = input("\nEnter skills (comma-separated): ").strip()
            if not skills:
                print("❌ No skills entered")
                return
            skill_list = [f'"{s.strip()}"' for s in skills.split(',')]
            cmd = f"python3 discover_book_ids.py --skills {' '.join(skill_list)}"
        else:
            print("Please run discovery first or use the new JSON format.")
            return
        
        print(f"\n🔍 Discovering book IDs...")
        print(f"Command: {cmd}\n")
        success, stdout, stderr = run_command(cmd, show_output=True)
        
        if not success:
            print("\n❌ Discovery failed!")
            return
        print("\n✅ Discovery completed!")
    
    # Now run download
    print("\n" + "=" * 60)
    print("Step 2: Download Books")
    print("=" * 60)
    
    print("\nSelect download option:")
    if json_file_path:
        # New format - show relevant options
        print("1. Download all books from JSON file")
        print("2. Test run (dry run) - preview what would be downloaded")
        print("3. Force re-download all books (updates existing)")
        print("4. Custom configuration (EPUB format, token settings, etc.)")
    else:
        # Current format - show all options
        print("1. Download all discovered books")
        print("2. Download specific skills")
        print("3. Test run (dry run)")
        print("4. Download priority skills only")
        print("5. Force re-download all books (updates existing)")
        print("6. Custom configuration")
    
    # Build base command
    base_cmd = "python3 download_books.py"
    if json_file_path:
        base_cmd += f" --json-file {json_file_path}"
    
    if json_file_path:
        # New format menu (1-4)
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            print("\n📚 Downloading all books from JSON file...")
            cmd = base_cmd
            
        elif choice == "2":
            print("\n🔍 Running test (dry run)...")
            cmd = f"{base_cmd} --dry-run"
            
        elif choice == "3":
            print("\n🔄 Force re-downloading all books (will overwrite existing EPUBs)...")
            confirm_force = input("Are you sure? This will re-download ALL books (y/N): ").strip().lower()
            if confirm_force != 'y':
                print("Cancelled.")
                return
            cmd = f"{base_cmd} --force"
            
        elif choice == "4":
            print("\n⚙️  Custom configuration options:")
            max_books = input("Max books to download (default: all): ").strip()
            format_choice = input("EPUB format (enhanced/kindle/dual/legacy, default dual): ").strip() or "dual"
            force_redownload = input("Force re-download existing books? (y/N): ").strip().lower()
            token_save = input("Save tokens after N books (default: 5): ").strip()
            
            cmd = f"{base_cmd} --format {format_choice}"
            if max_books:
                cmd += f" --max-books {max_books}"
            if force_redownload == 'y':
                cmd += " --force"
            if token_save and token_save.isdigit():
                cmd += f" --token-save-interval {token_save}"
            
        else:
            print("❌ Invalid choice")
            return
    else:
        # Current format menu (1-6)
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            print("\n📚 Downloading all discovered books...")
            cmd = base_cmd
            
        elif choice == "2":
            skills = input("\nEnter skills (comma-separated): ").strip()
            if not skills:
                print("❌ No skills entered")
                return
            
            skill_list = [f'"{s.strip()}"' for s in skills.split(',')]
            cmd = f"{base_cmd} --skills {' '.join(skill_list)}"
            
        elif choice == "3":
            print("\n🔍 Running test (dry run)...")
            cmd = f"{base_cmd} --dry-run"
            
        elif choice == "4":
            print("\n⭐ Downloading priority skills...")
            cmd = f'{base_cmd} --skills "Python" "Machine Learning" "AI & ML" "Data Science" "Deep Learning" --max-books 20'
            
        elif choice == "5":
            print("\n🔄 Force re-downloading all books (will overwrite existing EPUBs)...")
            confirm_force = input("Are you sure? This will re-download ALL books (y/N): ").strip().lower()
            if confirm_force != 'y':
                print("Cancelled.")
                return
            cmd = f"{base_cmd} --force"
            
        elif choice == "6":
            print("\n⚙️  Custom configuration options:")
            max_books = input("Max books per skill (default: all): ").strip()
            format_choice = input("EPUB format (enhanced/kindle/dual/legacy, default dual): ").strip() or "dual"
            force_redownload = input("Force re-download existing books? (y/N): ").strip().lower()
            token_save = input("Save tokens after N books (default: 5): ").strip()
            
            cmd = f"{base_cmd} --format {format_choice}"
            if max_books:
                cmd += f" --max-books {max_books}"
            if force_redownload == 'y':
                cmd += " --force"
            if token_save and token_save.isdigit():
                cmd += f" --token-save-interval {token_save}"
            
        else:
            print("❌ Invalid choice")
            return
    
    # Confirm before running
    print(f"\nCommand to run: {cmd}")
    confirm = input("Proceed? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("Cancelled.")
        return
    
    print(f"\n🚀 Starting download...")
    print("=" * 60)
    print()
    
    # Run the command with live output
    success, stdout, stderr = run_command(cmd, show_output=True)
    
    if success:
        print("\n✅ Download completed successfully!")
    else:
        print("\n❌ Download encountered issues!")
    
    print("\n📁 Check the following for results:")
    print("- books_by_skills/ - Downloaded books organized by skill")
    print("- output/download_results.json - Summary of download results")
    print("- logs/book_downloader.log - Detailed execution log")

if __name__ == "__main__":
    main()
