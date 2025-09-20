# SafariBooks Project Structure

This document describes the organized structure of the SafariBooks project after cleanup and reorganization.

## 📁 Directory Structure

```
safaribooks/
├── 📚 Core Scripts
│   ├── safaribooks.py              # Original monolithic script
│   ├── safaribooks_refactored.py   # Refactored version with improvements
│   └── examples.py                 # Comprehensive usage examples
│
├── 🔧 Utilities
│   ├── debug_auth.py               # Authentication debugging tool
│   ├── parallel.sh                 # Parallel download script
│   └── setup.py                    # Package setup script
│
├── 🧪 Tests
│   ├── run_tests.py                # Test runner
│   ├── test_auth.py                # Authentication tests
│   ├── test_comparison.py          # Original vs refactored comparison
│   ├── test_download.py            # Download functionality tests
│   ├── test_metadata_extraction.py # Metadata extraction tests
│   ├── test_refactored.py          # Refactored version tests
│   ├── unit/
│   │   └── test_auth/
│   │       └── test_session_manager.py # Unit tests for SessionManager
│   ├── integration/                # Integration tests (empty)
│   └── examples/                   # Example tests (empty)
│
├── 🏗️ Modular Structure (Partial)
│   └── oreilly_scraper/
│       ├── __init__.py
│       └── auth/
│           ├── __init__.py
│           ├── exceptions.py
│           ├── session_manager.py
│           └── README.md
│
├── 📖 Documentation
│   ├── README.md                   # Main project documentation
│   ├── REFACTORED_README.md        # Refactored version documentation
│   ├── COOKIE_SETUP.md             # Cookie extraction instructions
│   ├── METADATA_IMPROVEMENTS.md    # Metadata extraction documentation
│   ├── PROJECT_STRUCTURE.md        # This file
│   └── LICENSE.md                  # License information
│
├── ⚙️ Configuration
│   ├── config/
│   │   └── default_config.yaml     # Default configuration
│   ├── cookies.json                # Authentication cookies
│   ├── requirements.txt            # Python dependencies
│   ├── requirements_auth.txt       # Authentication dependencies
│   ├── Pipfile                     # Pipenv configuration
│   └── Pipfile.lock                # Pipenv lock file
│
├── 📚 Downloaded Content
│   └── Books/                      # Downloaded books directory
│       └── [Book folders with EPUB files]
│
└── 🔍 Legacy Parser
    └── OReilly_Book_ID_Parser/     # Legacy book ID parser
        ├── README.md
        ├── safari_books_online_parser.py
        └── [category files]
```

## 🎯 File Categories

### Core Scripts
- **`safaribooks.py`**: Original monolithic script with all functionality
- **`safaribooks_refactored.py`**: Improved version with better structure and EPUB fixes
- **`examples.py`**: Comprehensive examples for all functionality

### Utilities
- **`debug_auth.py`**: Consolidated authentication debugging tool
- **`parallel.sh`**: Shell script for parallel downloads
- **`setup.py`**: Python package setup

### Tests
- **`run_tests.py`**: Main test runner with different test categories
- **`test_*.py`**: Various test files for different components
- **`unit/`**: Unit tests for individual components
- **`integration/`**: Integration tests for full workflows
- **`examples/`**: Example tests for demonstration

### Documentation
- **`README.md`**: Main project documentation
- **`COOKIE_SETUP.md`**: Manual cookie extraction instructions
- **`METADATA_IMPROVEMENTS.md`**: Metadata extraction improvements
- **`PROJECT_STRUCTURE.md`**: This structure documentation

### Configuration
- **`config/`**: Configuration files
- **`cookies.json`**: Authentication cookies
- **`requirements.txt`**: Python dependencies

## 🚀 Usage

### Running Tests
```bash
# Run all tests
python tests/run_tests.py

# Run specific test types
python tests/run_tests.py --type unit
python tests/run_tests.py --type integration
python tests/run_tests.py --type examples

# Verbose output
python tests/run_tests.py --verbose
```

### Running Examples
```bash
# Run comprehensive examples
python examples.py
```

### Debugging Authentication
```bash
# Debug authentication issues
python debug_auth.py
```

### Downloading Books
```bash
# Using refactored version (recommended)
python safaribooks_refactored.py 9780136766803

# Using original version
python safaribooks.py 9780136766803
```

## 🔄 Migration Notes

### Removed Files
The following duplicate/unnecessary files were removed during cleanup:
- `debug_refactored_auth.py` → merged into `debug_auth.py`
- `check_login_urls.py` → merged into `debug_auth.py`
- `example_download.py` → merged into `examples.py`
- `example_usage.py` → merged into `examples.py`
- `register_user.py` → unused legacy file
- `retrieve_cookies.py` → replaced by `COOKIE_SETUP.md`
- `sso_cookies.py` → unused legacy file
- `interactive_login.py` → unused legacy file
- `get_cookies_console.js` → replaced by `COOKIE_SETUP.md`
- Various log files → cleaned up

### Consolidated Functionality
- **Authentication debugging**: All debug functionality consolidated into `debug_auth.py`
- **Examples**: All example usage consolidated into `examples.py`
- **Tests**: All tests organized in `tests/` directory with proper structure

## 📋 Next Steps

1. **Complete modular structure**: Finish implementing the `oreilly_scraper/` module
2. **Add more tests**: Expand test coverage for all components
3. **Documentation**: Add more detailed documentation for each component
4. **CI/CD**: Set up automated testing and deployment

## 🤝 Contributing

When adding new files:
1. Place tests in appropriate `tests/` subdirectories
2. Add examples to `examples.py`
3. Update this documentation
4. Follow the established naming conventions
