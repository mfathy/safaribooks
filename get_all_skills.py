#!/usr/bin/env python3
"""
Get All Skills from O'Reilly Learning
This script discovers and lists all available skills on O'Reilly Learning platform
"""

import sys
import os
import time
from datetime import datetime

# Add the oreilly_parser directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'oreilly_parser'))

from oreilly_skills_parser import discover_all_skills, load_cookies

def main():
    """Main function to discover all O'Reilly Learning skills"""
    print("🔍 O'Reilly Learning Skills Discovery")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load authentication cookies
    cookies = load_cookies()
    if not cookies:
        print("⚠️  No authentication cookies found!")
        print("Some content may not be accessible without authentication")
        print("You can get cookies by:")
        print("1. Logging into learning.oreilly.com in your browser")
        print("2. Using browser dev tools to copy cookies")
        print("3. Saving them to cookies.json file")
        print("\nContinuing without authentication...")
    else:
        print("✅ Authentication cookies loaded")
    
    # Discover all skills
    print("\n🚀 Starting skills discovery...")
    start_time = time.time()
    
    try:
        skills = discover_all_skills(cookies, verbose=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n🎉 Skills discovery completed!")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📚 Found {len(skills)} unique skills")
        
        # Show summary statistics
        print(f"\n📊 Summary:")
        print(f"   🔍 Total skills discovered: {len(skills)}")
        print(f"   ⏱️  Discovery duration: {duration:.1f} seconds")
        print(f"   📄 Average time per skill: {duration/len(skills):.3f} seconds" if skills else "   📄 No skills found")
        
        # Show first 20 skills as preview
        if skills:
            print(f"\n📋 Preview of discovered skills:")
            for i, skill in enumerate(skills[:20]):
                print(f"   {i+1:2d}. {skill}")
            if len(skills) > 20:
                print(f"   ... and {len(skills) - 20} more skills")
        
        return True
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Skills discovery interrupted by user")
        print(f"📊 Partial results may be available in oreilly-skills.json")
        return False
    except Exception as e:
        print(f"\n❌ Error during skills discovery: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python3 get_all_skills.py")
        print("\nThis script will:")
        print("  - Discover all available skills on O'Reilly Learning")
        print("  - Use multiple discovery methods (web scraping, API, search suggestions)")
        print("  - Save skills to oreilly-skills.json and oreilly-skills.txt")
        print("  - Show progress and statistics")
        print("\nRequirements:")
        print("  - Optional: cookies.json file with O'Reilly Learning authentication")
        print("  - Internet connection")
    else:
        success = main()
        
        if success:
            print(f"\n✅ Skills discovery completed successfully!")
            print(f"📁 Check the generated files:")
            print(f"   - oreilly-skills.json (detailed format with metadata)")
            print(f"   - oreilly-skills.txt (simple list of skills)")
        else:
            print(f"\n❌ Skills discovery failed")
            sys.exit(1)
