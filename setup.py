#!/usr/bin/env python3
"""
Setup script for Oreilly Refactored.

This script helps install the required dependencies for the refactored Oreilly code.
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install required dependencies."""
    print("Installing required dependencies for Oreilly Refactored...")
    
    dependencies = ['requests>=2.20.0', 'lxml>=4.1.1']
    
    for dep in dependencies:
        print(f"Installing {dep}...")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', '--break-system-packages', dep
            ])
            print(f"✅ {dep} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {dep}: {e}")
            return False
    
    return True

def test_installation():
    """Test that the installation worked."""
    print("\nTesting installation...")
    
    try:
        import requests
        import lxml
        print("✅ All dependencies imported successfully")
        
        # Test our refactored code
        from safaribooks_refactored import download_book, parse_cred
        print("✅ Oreilly refactored code imported successfully")
        
        # Test parse_cred function
        result = parse_cred("test@example.com:password123")
        if result == ("test@example.com", "password123"):
            print("✅ parse_cred function works correctly")
        else:
            print("❌ parse_cred function test failed")
            return False
            
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main setup function."""
    print("=" * 60)
    print("Oreilly Refactored Setup")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("safaribooks_refactored.py"):
        print("❌ Error: safaribooks_refactored.py not found in current directory")
        print("Please run this script from the Oreilly project directory")
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed: Could not install dependencies")
        return False
    
    # Test installation
    if not test_installation():
        print("❌ Setup failed: Installation test failed")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Setup completed successfully!")
    print("=" * 60)
    print("\nYou can now use Oreilly Refactored:")
    print("\n1. CLI Usage:")
    print("   python3 safaribooks_refactored.py 9780136766803")
    print("   python3 safaribooks_refactored.py --cred 'email:password' 9780136766803")
    print("\n2. Programmatic Usage:")
    print("   from safaribooks_refactored import download_book")
    print("   book_path = download_book('9780136766803', '/path/to/books')")
    print("\n3. See examples:")
    print("   python3 example_download.py")
    print("\n4. Run tests:")
    print("   python3 test_comparison.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
