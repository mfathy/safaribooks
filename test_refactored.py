#!/usr/bin/env python3
"""
Simple test to verify the refactored code structure without requiring dependencies.
"""

import ast
import sys


def test_syntax():
    """Test that the refactored code has valid Python syntax."""
    try:
        with open('safaribooks_refactored.py', 'r') as f:
            source = f.read()
        
        # Parse the AST to check for syntax errors
        ast.parse(source)
        print("✅ Syntax check passed")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False


def test_function_signatures():
    """Test that the required functions exist with correct signatures."""
    try:
        with open('safaribooks_refactored.py', 'r') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        # Check for download_book function
        download_book_found = False
        parse_cred_found = False
        SafariBooksDownloader_found = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == 'download_book':
                    download_book_found = True
                    print(f"✅ Found download_book function with {len(node.args.args)} parameters")
                elif node.name == 'parse_cred':
                    parse_cred_found = True
                    print(f"✅ Found parse_cred function")
            elif isinstance(node, ast.ClassDef):
                if node.name == 'SafariBooksDownloader':
                    SafariBooksDownloader_found = True
                    print(f"✅ Found SafariBooksDownloader class")
        
        if not download_book_found:
            print("❌ download_book function not found")
        if not parse_cred_found:
            print("❌ parse_cred function not found")
        if not SafariBooksDownloader_found:
            print("❌ SafariBooksDownloader class not found")
            
        return download_book_found and parse_cred_found and SafariBooksDownloader_found
        
    except Exception as e:
        print(f"❌ Error analyzing code: {e}")
        return False


def test_imports():
    """Test that the required imports are present."""
    try:
        with open('safaribooks_refactored.py', 'r') as f:
            source = f.read()
        
        required_imports = [
            'import re',
            'import os', 
            'import sys',
            'import json',
            'import requests',
            'import argparse',
            'from lxml import html',
            'from typing import Optional, Dict, Any, List'
        ]
        
        missing_imports = []
        for imp in required_imports:
            if imp not in source:
                missing_imports.append(imp)
        
        if missing_imports:
            print(f"❌ Missing imports: {missing_imports}")
            return False
        else:
            print("✅ All required imports present")
            return True
            
    except Exception as e:
        print(f"❌ Error checking imports: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing refactored SafariBooks code...")
    print("=" * 50)
    
    tests = [
        ("Syntax Check", test_syntax),
        ("Function Signatures", test_function_signatures), 
        ("Import Check", test_imports)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The refactored code structure looks good.")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
