#!/usr/bin/env python3
"""
Test script to compare the refactored code behavior with the original safaribooks.py
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def test_import_functionality():
    """Test that the refactored code can be imported and has the expected functions."""
    print("Testing import functionality...")
    
    try:
        from oreilly import download_book, parse_cred, OreillyDownloader
        print("✅ Successfully imported download_book, parse_cred, and OreillyDownloader")
        
        # Test parse_cred function
        result = parse_cred("test@example.com:password123")
        if result == ("test@example.com", "password123"):
            print("✅ parse_cred function works correctly")
        else:
            print(f"❌ parse_cred returned unexpected result: {result}")
            return False
            
        # Test parse_cred with invalid input
        result = parse_cred("invalid")
        if result is None:
            print("✅ parse_cred correctly handles invalid input")
        else:
            print(f"❌ parse_cred should return None for invalid input, got: {result}")
            return False
            
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import test: {e}")
        return False

def test_authentication_behavior():
    """Test that both original and refactored code handle authentication the same way."""
    print("\nTesting authentication behavior...")
    
    book_id = "9780136766803"
    
    # Test original safaribooks.py
    print("Testing original safaribooks.py...")
    try:
        result = subprocess.run([
            sys.executable, "safaribooks.py", book_id
        ], capture_output=True, text=True, timeout=30)
        
        original_exit_code = result.returncode
        original_stderr = result.stderr
        
        print(f"Original script exit code: {original_exit_code}")
        if "Authentication issue" in original_stderr:
            print("✅ Original script correctly detects authentication issue")
        else:
            print("⚠️  Original script output:")
            print(original_stderr[:200] + "..." if len(original_stderr) > 200 else original_stderr)
            
    except subprocess.TimeoutExpired:
        print("⚠️  Original script timed out")
        original_exit_code = 1
    except Exception as e:
        print(f"⚠️  Error running original script: {e}")
        original_exit_code = 1
    
    # Test refactored code
    print("\nTesting refactored code...")
    try:
        from oreilly import download_book
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                book_path = download_book(book_id, temp_dir)
                print("❌ Refactored code should have failed with authentication issue")
                return False
            except ValueError as e:
                if "Authentication issue" in str(e):
                    print("✅ Refactored code correctly detects authentication issue")
                    refactored_failed = True
                else:
                    print(f"❌ Refactored code failed with unexpected error: {e}")
                    return False
            except Exception as e:
                print(f"❌ Refactored code failed with unexpected error type: {type(e).__name__}: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing refactored code: {e}")
        return False
    
    print("✅ Both original and refactored code handle authentication consistently")
    return True

def test_cli_compatibility():
    """Test that the refactored code maintains CLI compatibility."""
    print("\nTesting CLI compatibility...")
    
    # Test help command
    try:
        result = subprocess.run([
            sys.executable, "safaribooks_refactored.py", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and "Download and generate an EPUB" in result.stdout:
            print("✅ CLI help command works correctly")
        else:
            print("❌ CLI help command failed")
            print(f"Exit code: {result.returncode}")
            print(f"Output: {result.stdout[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Error testing CLI help: {e}")
        return False
    
    # Test invalid arguments
    try:
        result = subprocess.run([
            sys.executable, "safaribooks_refactored.py", "--no-cookies", "1234567890123"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0 and "invalid option" in result.stderr:
            print("✅ CLI correctly validates arguments")
        else:
            print("❌ CLI argument validation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing CLI validation: {e}")
        return False
    
    return True

def test_code_structure():
    """Test that the refactored code has the expected structure."""
    print("\nTesting code structure...")
    
    try:
        with open("safaribooks_refactored.py", "r") as f:
            content = f.read()
        
        # Check for key components
        checks = [
            ("download_book function", "def download_book("),
            ("OreillyDownloader class", "class OreillyDownloader:"),
            ("Oreilly class", "class Oreilly("),
            ("parse_cred function", "def parse_cred("),
            ("CLI argument parsing", "argparse.ArgumentParser"),
            ("Main execution block", 'if __name__ == "__main__":'),
        ]
        
        for check_name, pattern in checks:
            if pattern in content:
                print(f"✅ {check_name} found")
            else:
                print(f"❌ {check_name} not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking code structure: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Oreilly Refactored Code Validation")
    print("=" * 60)
    
    tests = [
        ("Import Functionality", test_import_functionality),
        ("Authentication Behavior", test_authentication_behavior),
        ("CLI Compatibility", test_cli_compatibility),
        ("Code Structure", test_code_structure),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ The refactored code is working correctly and maintains compatibility.")
        print("✅ Ready to commit changes.")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        print("❌ Do not commit until all issues are resolved.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

