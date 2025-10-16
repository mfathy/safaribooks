#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
O'Reilly Books Automation - Master Coordinator
Coordinates the two-step process: Discovery → Download
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Optional


class OReillyAutomation:
    """Master coordinator for the two-step automation process"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or 'download_config.json'
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
        
        # Return minimal default config
        return {
            'book_ids_directory': 'book_ids',
            'base_directory': 'books_by_skills',
            'skills_file': 'my_favorite_skills.txt'
        }
    
    def run_command(self, cmd: str, description: str) -> bool:
        """Run a command and return success status"""
        print(f"\n{'='*60}")
        print(f"🚀 {description}")
        print(f"{'='*60}")
        print(f"Command: {cmd}")
        
        try:
            result = subprocess.run(cmd, shell=True, check=True)
            print(f"✅ {description} completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} failed with exit code {e.returncode}")
            return False
        except Exception as e:
            print(f"❌ Error running {description}: {e}")
            return False
    
    def step1_discover(self, skills: List[str] = None, **kwargs) -> bool:
        """Step 1: Discover book IDs for all skills"""
        cmd_parts = ["python3 discover_book_ids.py"]
        
        if self.config_file != 'download_config.json':
            cmd_parts.append(f"--config {self.config_file}")
        
        if skills:
            skill_args = " ".join([f'"{s}"' for s in skills])
            cmd_parts.append(f"--skills {skill_args}")
        
        # Add additional arguments
        for key, value in kwargs.items():
            if key == 'max_pages':
                cmd_parts.append(f"--max-pages {value}")
            elif key == 'workers':
                cmd_parts.append(f"--workers {value}")
            elif key == 'verbose':
                cmd_parts.append("--verbose")
            elif key == 'dry_run':
                cmd_parts.append("--dry-run")
        
        cmd = " ".join(cmd_parts)
        return self.run_command(cmd, "Step 1: Book ID Discovery")
    
    def step2_download(self, skills: List[str] = None, **kwargs) -> bool:
        """Step 2: Download books from discovered IDs"""
        cmd_parts = ["python3 download_books.py"]
        
        if self.config_file != 'download_config.json':
            cmd_parts.append(f"--config {self.config_file}")
        
        if skills:
            skill_args = " ".join([f'"{s}"' for s in skills])
            cmd_parts.append(f"--skills {skill_args}")
        
        # Add additional arguments
        for key, value in kwargs.items():
            if key == 'max_books':
                cmd_parts.append(f"--max-books {value}")
            elif key == 'workers':
                cmd_parts.append(f"--workers {value}")
            elif key == 'format':
                cmd_parts.append(f"--format {value}")
            elif key == 'verbose':
                cmd_parts.append("--verbose")
            elif key == 'dry_run':
                cmd_parts.append("--dry-run")
        
        cmd = " ".join(cmd_parts)
        return self.run_command(cmd, "Step 2: Book Download")
    
    def run_full_automation(self, skills: List[str] = None, **kwargs) -> bool:
        """Run both steps in sequence"""
        print("🎯 Starting Full O'Reilly Books Automation")
        print("This will run both discovery and download steps")
        
        # Step 1: Discovery
        discovery_success = self.step1_discover(skills, **kwargs)
        if not discovery_success:
            print("❌ Discovery failed. Aborting full automation.")
            return False
        
        # Check if any books were discovered
        book_ids_dir = Path(self.config.get('book_ids_directory', 'book_ids'))
        if not book_ids_dir.exists() or not list(book_ids_dir.glob("*_books.json")):
            print("❌ No book IDs discovered. Aborting download step.")
            return False
        
        # Step 2: Download
        download_success = self.step2_download(skills, **kwargs)
        if not download_success:
            print("❌ Download failed.")
            return False
        
        print("\n🎉 Full automation completed successfully!")
        return True
    
    def show_status(self):
        """Show current status of discovery and download"""
        print("\n📊 Current Status")
        print("=" * 40)
        
        # Check discovery status
        book_ids_dir = Path(self.config.get('book_ids_directory', 'book_ids'))
        if book_ids_dir.exists():
            skill_files = list(book_ids_dir.glob("*_books.json"))
            if skill_files:
                total_books = 0
                for skill_file in skill_files:
                    try:
                        with open(skill_file, 'r') as f:
                            data = json.load(f)
                            total_books += data.get('total_books', 0)
                    except:
                        pass
                
                print(f"📚 Discovery: {len(skill_files)} skills, ~{total_books:,} books")
            else:
                print("📚 Discovery: No skill files found")
        else:
            print("📚 Discovery: Not started")
        
        # Check download status
        books_dir = Path(self.config.get('base_directory', 'books_by_skills'))
        if books_dir.exists():
            skill_dirs = [d for d in books_dir.iterdir() if d.is_dir()]
            if skill_dirs:
                print(f"📖 Downloads: {len(skill_dirs)} skill folders")
            else:
                print("📖 Downloads: No skill folders found")
        else:
            print("📖 Downloads: Not started")
        
        # Check progress files
        progress_files = [
            'discovery_progress.json',
            'download_progress.json',
            'discovery_results.json',
            'download_results.json'
        ]
        
        print("\n📋 Progress Files:")
        for pf in progress_files:
            if os.path.exists(pf):
                print(f"  ✅ {pf}")
            else:
                print(f"  ⏸️  {pf}")
    
    def show_progress(self, progress_type: str = "all"):
        """Show detailed progress with statistics and ETA"""
        from progress_tracker import ProgressTracker
        
        if progress_type in ["all", "discovery"]:
            discovery_file = self.config.get('discovery_progress_file', 'discovery_progress.json')
            if os.path.exists(discovery_file):
                print("\n🔍 DISCOVERY PROGRESS")
                tracker = ProgressTracker(discovery_file, "discovery")
                tracker.print_summary()
            elif progress_type == "discovery":
                print("\n📊 No discovery progress found")
                print("Run: python3 discover_book_ids.py\n")
        
        if progress_type in ["all", "download"]:
            download_file = self.config.get('progress_file', 'download_progress.json')
            if os.path.exists(download_file):
                print("\n📥 DOWNLOAD PROGRESS")
                tracker = ProgressTracker(download_file, "download")
                tracker.print_summary()
            elif progress_type == "download":
                print("\n📊 No download progress found")
                print("Run: python3 download_books.py\n")
    
    def cleanup(self, confirm: bool = False):
        """Clean up generated files and directories"""
        if not confirm:
            response = input("Are you sure you want to clean up all generated files? (y/N): ")
            if response.lower() != 'y':
                print("Cleanup cancelled.")
                return
        
        print("🧹 Cleaning up generated files...")
        
        # Files to remove
        files_to_remove = [
            'discovery_progress.json',
            'download_progress.json',
            'discovery_results.json',
            'download_results.json',
            'discovery_summary.txt',
            'book_id_discovery.log',
            'book_downloader.log',
            'skill_downloader.log'
        ]
        
        # Directories to remove
        dirs_to_remove = [
            self.config.get('book_ids_directory', 'book_ids'),
            self.config.get('base_directory', 'books_by_skills'),
            self.config.get('temp_directory', 'temp_discovery')
        ]
        
        # Remove files
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"  🗑️  Removed: {file_path}")
        
        # Remove directories
        for dir_path in dirs_to_remove:
            if os.path.exists(dir_path):
                import shutil
                shutil.rmtree(dir_path)
                print(f"  🗑️  Removed directory: {dir_path}")
        
        print("✅ Cleanup completed!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="O'Reilly Books Automation - Master Coordinator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full automation (discovery + download)
  python3 oreilly_automation.py --full
  
  # Run only discovery step
  python3 oreilly_automation.py --discover
  
  # Run only download step
  python3 oreilly_automation.py --download
  
  # Run for specific skills
  python3 oreilly_automation.py --full --skills "Python" "Machine Learning"
  
  # Test run (dry run)
  python3 oreilly_automation.py --full --dry-run
  
  # Show current status
  python3 oreilly_automation.py --status
  
  # Clean up all generated files
  python3 oreilly_automation.py --cleanup
        """
    )
    
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--full', action='store_true', help='Run full automation (discovery + download)')
    parser.add_argument('--discover', action='store_true', help='Run only discovery step')
    parser.add_argument('--download', action='store_true', help='Run only download step')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--progress', action='store_true', help='Show detailed progress with ETA')
    parser.add_argument('--progress-type', choices=['all', 'discovery', 'download'], default='all',
                       help='Type of progress to show (default: all)')
    parser.add_argument('--cleanup', action='store_true', help='Clean up generated files')
    parser.add_argument('--skills', '-s', nargs='+', help='Specific skills to process')
    parser.add_argument('--max-pages', type=int, help='Maximum API pages per skill (discovery)')
    parser.add_argument('--max-books', type=int, help='Maximum books per skill (download)')
    parser.add_argument('--workers', type=int, help='Number of concurrent threads')
    parser.add_argument('--format', choices=['legacy', 'enhanced', 'kindle', 'dual'], 
                       help='EPUB format to generate (download)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without actually doing it')
    
    args = parser.parse_args()
    
    # Initialize automation coordinator
    automation = OReillyAutomation(args.config)
    
    # Prepare common arguments
    common_args = {}
    if args.max_pages:
        common_args['max_pages'] = args.max_pages
    if args.workers:
        common_args['workers'] = args.workers
    if args.verbose:
        common_args['verbose'] = True
    if args.dry_run:
        common_args['dry_run'] = True
    
    download_args = common_args.copy()
    if args.max_books:
        download_args['max_books'] = args.max_books
    if args.format:
        download_args['format'] = args.format
    
    try:
        if args.status:
            automation.show_status()
        
        elif args.progress:
            automation.show_progress(args.progress_type)
        
        elif args.cleanup:
            automation.cleanup()
        
        elif args.full:
            success = automation.run_full_automation(args.skills, **common_args)
            sys.exit(0 if success else 1)
        
        elif args.discover:
            success = automation.step1_discover(args.skills, **common_args)
            sys.exit(0 if success else 1)
        
        elif args.download:
            success = automation.step2_download(args.skills, **download_args)
            sys.exit(0 if success else 1)
        
        else:
            # Interactive mode
            print("🎯 O'Reilly Books Automation")
            print("Choose an option:")
            print("1. Full automation (discovery + download)")
            print("2. Discovery only")
            print("3. Download only")
            print("4. Show status")
            print("5. Show progress (with ETA)")
            print("6. Cleanup")
            
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == "1":
                success = automation.run_full_automation(args.skills, **common_args)
                sys.exit(0 if success else 1)
            elif choice == "2":
                success = automation.step1_discover(args.skills, **common_args)
                sys.exit(0 if success else 1)
            elif choice == "3":
                success = automation.step2_download(args.skills, **download_args)
                sys.exit(0 if success else 1)
            elif choice == "4":
                automation.show_status()
            elif choice == "5":
                automation.show_progress("all")
            elif choice == "6":
                automation.cleanup()
            else:
                print("Invalid choice")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
