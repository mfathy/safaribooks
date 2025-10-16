#!/usr/bin/env python3
"""
Quick Download Script - Simplified interface for common use cases
"""

import sys
import os
import subprocess

def run_command(cmd):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    """Interactive quick download interface"""
    print("🚀 O'Reilly Books Quick Downloader")
    print("=" * 50)
    
    # Check if cookies.json exists
    if not os.path.exists('cookies.json'):
        print("❌ Error: cookies.json not found!")
        print("Please set up your O'Reilly authentication first.")
        print("See COOKIE_SETUP.md for instructions.")
        return
    
    print("✅ Authentication cookies found")
    
    # Show options
    print("\nSelect download option:")
    print("1. Download all favorite skills (recommended)")
    print("2. Download specific skills")
    print("3. Test run (dry run)")
    print("4. Download top priority skills only")
    print("5. Custom configuration")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        print("\n📚 Downloading all favorite skills...")
        cmd = "python automate_skill_downloads.py"
        
    elif choice == "2":
        skills = input("\nEnter skills (comma-separated): ").strip()
        if not skills:
            print("❌ No skills entered")
            return
        
        skill_list = [f'"{s.strip()}"' for s in skills.split(',')]
        cmd = f"python automate_skill_downloads.py --skills {' '.join(skill_list)}"
        
    elif choice == "3":
        print("\n🔍 Running test (dry run)...")
        cmd = "python automate_skill_downloads.py --dry-run"
        
    elif choice == "4":
        print("\n⭐ Downloading priority skills...")
        cmd = "python automate_skill_downloads.py --skills \"Python\" \"Machine Learning\" \"AI & ML\" \"Data Science\" \"Deep Learning\" --max-books 20"
        
    elif choice == "5":
        print("\n⚙️  Custom configuration options:")
        max_books = input("Max books per skill (default 30): ").strip() or "30"
        workers = input("Concurrent workers (default 2): ").strip() or "2"
        format_choice = input("EPUB format (enhanced/kindle/dual/legacy, default enhanced): ").strip() or "enhanced"
        
        cmd = f"python automate_skill_downloads.py --max-books {max_books} --workers {workers} --format {format_choice}"
        
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
    print("=" * 50)
    
    # Run the command
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print("✅ Download completed successfully!")
        if stdout:
            print(stdout)
    else:
        print("❌ Download failed!")
        if stderr:
            print("Error:", stderr)
        if stdout:
            print("Output:", stdout)
    
    print("\n📁 Check the following for results:")
    print("- books_by_skills/ - Downloaded books organized by skill")
    print("- download_results.json - Summary of download results")
    print("- skill_downloader.log - Detailed execution log")

if __name__ == "__main__":
    main()
