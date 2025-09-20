#!/usr/bin/env python3
"""
Test runner for SafariBooks project.

This script runs all tests in the project with proper organization:
- Unit tests (fast, isolated)
- Integration tests (slower, require authentication)
- Example tests (demonstration purposes)
"""

import os
import sys
import unittest
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def discover_and_run_tests(test_type="all", verbose=False):
    """Discover and run tests based on type."""
    
    # Test directories
    test_dirs = {
        "unit": ["tests/unit"],
        "integration": ["tests"],
        "examples": ["tests/examples"],
        "all": ["tests"]
    }
    
    if test_type not in test_dirs:
        print(f"❌ Unknown test type: {test_type}")
        print(f"Available types: {', '.join(test_dirs.keys())}")
        return False
    
    # Discover tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for test_dir in test_dirs[test_type]:
        if os.path.exists(test_dir):
            discovered = loader.discover(test_dir, pattern="test_*.py")
            suite.addTest(discovered)
            print(f"📁 Discovered tests in: {test_dir}")
        else:
            print(f"⚠️  Test directory not found: {test_dir}")
    
    if suite.countTestCases() == 0:
        print("❌ No tests found")
        return False
    
    # Run tests
    print(f"\n🧪 Running {suite.countTestCases()} test(s)...")
    print("=" * 50)
    
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print(f"\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    return result.wasSuccessful()

def check_prerequisites():
    """Check if prerequisites for testing are met."""
    print("🔍 Checking Test Prerequisites")
    print("=" * 40)
    
    # Check if main files exist
    required_files = [
        "safaribooks.py",
        "safaribooks_refactored.py",
        "cookies.json"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
        else:
            print(f"✅ {file}")
    
    if missing_files:
        print(f"\n⚠️  Missing files: {', '.join(missing_files)}")
        if "cookies.json" in missing_files:
            print("   Run debug_auth.py to check authentication setup")
        return False
    
    print("✅ All prerequisites met")
    return True

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run SafariBooks tests")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "examples", "all"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check prerequisites, don't run tests"
    )
    
    args = parser.parse_args()
    
    print("🧪 SafariBooks Test Runner")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix issues above.")
        return 1
    
    if args.check_only:
        print("\n✅ Prerequisites check completed")
        return 0
    
    # Run tests
    success = discover_and_run_tests(args.type, args.verbose)
    
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
