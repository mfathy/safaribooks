#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to demonstrate the V1 discover updates
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from discover_book_ids import BookIDDiscoverer

def test_skill_variants():
    """Test the skill variants generation"""
    print("=" * 60)
    print("Testing Skill Variants Generation")
    print("=" * 60)
    
    discoverer = BookIDDiscoverer()
    
    test_skills = [
        "Engineering Leadership",
        "AI & ML",
        "Machine Learning",
        "Data Science",
        "Python Programming"
    ]
    
    for skill in test_skills:
        variants = discoverer._get_skill_variants(skill)
        print(f"\n📚 Skill: '{skill}'")
        print(f"   Variants ({len(variants)}):")
        for variant in sorted(variants):
            print(f"   - {variant}")

def test_validation_logic():
    """Demonstrate validation logic"""
    print("\n" + "=" * 60)
    print("Validation Logic Overview")
    print("=" * 60)
    
    print("""
✅ UPDATED VALIDATIONS:

1. Title Length: Now accepts titles >= 5 characters (was 10)
   - Example: "R Tips" would now pass validation
   
2. Chapter Keywords: Removed 'part' and 'parts'
   - Books like "Python Parts: Essential Tools" are now included
   
3. Subject Validation: NEW - Books must have matching subjects
   - Checks if book subjects contain the skill or its variants
   - Example: For "Engineering Leadership", checks for:
     * "engineering leadership"
     * "engineering"
     * "leadership"
     * "engineering-leadership"
     * etc.
     
4. Topics Validation: NEW - Books must have matching topics
   - Similar to subject validation but for topics field
   
5. Pagination: Stops at EXACT count (no 10% buffer)
   - Fetches exactly the expected number of books
   
6. Skip Large Skills: Skills with >500 books are skipped
   - Focuses discovery on specific, manageable topics
    """)

def test_skipped_skills():
    """Show which skills would be skipped"""
    print("\n" + "=" * 60)
    print("Skills That Would Be Skipped (>500 books)")
    print("=" * 60)
    
    print("""
The following skills would be automatically skipped:
- Any skill with expected_book_count > 500
- These are usually very broad categories
- Helps focus on specific, relevant topics
    
To see actual skipped skills, run:
    python3 discover_book_ids.py --verbose
    """)

def main():
    """Main test function"""
    print("\n🧪 Testing Discover V1 Updates\n")
    
    try:
        test_skill_variants()
        test_validation_logic()
        test_skipped_skills()
        
        print("\n" + "=" * 60)
        print("✅ All Tests Completed!")
        print("=" * 60)
        print("""
To run actual discovery with new validation:
    python3 discover_book_ids.py --skills "Engineering Leadership"
    
To see detailed validation logs:
    python3 discover_book_ids.py --skills "Engineering Leadership" --verbose
    
For full documentation:
    cat docs/DISCOVER_V1_UPDATES.md
        """)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

