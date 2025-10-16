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
    
    if not book_ids_exist:
        print("\n⚠️  Book IDs not discovered yet. You must run Step 1 first.")
        print("\nSelect discovery option:")
        print("1. Discover all skills from my_favorite_skills.txt")
        print("2. Discover specific skills")
        print("3. Exit (run discovery manually)")
        
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
            print("Please run: python3 discover_book_ids.py")
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
    print("1. Download all discovered books")
    print("2. Download specific skills")
    print("3. Test run (dry run)")
    print("4. Download priority skills only")
    print("5. Custom configuration")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        print("\n📚 Downloading all discovered books...")
        cmd = "python3 download_books.py"
        
    elif choice == "2":
        skills = input("\nEnter skills (comma-separated): ").strip()
        if not skills:
            print("❌ No skills entered")
            return
        
        skill_list = [f'"{s.strip()}"' for s in skills.split(',')]
        cmd = f"python3 download_books.py --skills {' '.join(skill_list)}"
        
    elif choice == "3":
        print("\n🔍 Running test (dry run)...")
        cmd = "python3 download_books.py --dry-run"
        
    elif choice == "4":
        print("\n⭐ Downloading priority skills...")
        cmd = 'python3 download_books.py --skills "Python" "Machine Learning" "AI & ML" "Data Science" "Deep Learning" --max-books 20'
        
    elif choice == "5":
        print("\n⚙️  Custom configuration options:")
        max_books = input("Max books per skill (default: all): ").strip()
        format_choice = input("EPUB format (enhanced/kindle/dual/legacy, default dual): ").strip() or "dual"
        
        cmd = f"python3 download_books.py --format {format_choice}"
        if max_books:
            cmd += f" --max-books {max_books}"
        
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
