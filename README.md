# O'Reilly Learning Parser & Downloader

A comprehensive toolkit for parsing O'Reilly Learning topics and downloading books as EPUB files.

## Project Structure

```
oreilly-books/
├── book_downloader/          # Book downloader modules
│   ├── download.py           # Core download functionality
│   ├── epub.py              # Basic EPUB generator
│   ├── epub_enhanced.py     # Enhanced EPUB generator
│   ├── download_books.py    # Download manager
│   ├── auth.py              # Authentication
│   ├── display.py           # Display utilities
│   └── config.py            # Configuration
├── book_parser/              # Book parser modules
│   ├── topic_book_parser.py # Topic-specific parser
│   ├── oreilly_books_parser.py # All-topics parser
│   ├── auth.py              # Authentication
│   ├── display.py           # Display utilities
│   └── config.py            # Configuration
├── experiments/              # Experimental files
├── archive/                  # Archived files
├── books/                    # Downloaded books (EPUB format)
├── book_lists/              # Parsed book lists and IDs
├── topics/                  # Topic data and metadata
├── main_downloader.py       # Main downloader script
├── main_parser.py           # Main parser script
└── main_topic_downloader.py  # Combined topic parser + downloader
```

## Quick Start

### 1. Parse Topics (Extract Book IDs)

```bash
# Parse a specific topic
python main_parser.py topic generative-ai

# Parse all available topics
python main_parser.py all-topics

# Parse with custom settings
python main_parser.py topic python --max-pages 5 --delay 1.0
```

### 2. Download Books (From Book IDs)

```bash
# Download a single book
python main_downloader.py 9781098118723

# Download from book IDs file
python main_downloader.py --from-file book_lists/generative-ai_book_ids.json

# Download with custom settings
python main_downloader.py 9781098118723 --output-dir my_books --basic-epub
```

### 3. Topic Downloader (Parse + Download)

```bash
# Parse topic and download all books
python main_topic_downloader.py generative-ai

# Parse and download with custom settings
python main_topic_downloader.py python --max-pages 5 --delay 1.0

# Download from existing book IDs file
python main_topic_downloader.py --from-file book_lists/generative-ai_book_ids.json
```

## Features

### 🔍 **Topic Parser**
- Extract book IDs from specific topics
- Parse all available topics
- Handle API limitations gracefully
- Generate structured output (JSON, TXT)

### 📚 **Book Downloader**
- Download individual books as EPUB
- Batch download from book IDs files
- Enhanced and basic EPUB generation
- Progress tracking and error handling

### 🚀 **Topic Downloader**
- Combined workflow: parse topic + download books
- Streamlined process for complete topic downloads
- Flexible input options (topic name or book IDs file)

## Usage Examples

### Parse a Topic
```bash
# Basic topic parsing
python main_parser.py topic generative-ai

# Advanced parsing with custom settings
python main_parser.py topic python --max-pages 10 --delay 1.0 --output-dir my_results

# Parse all topics
python main_parser.py all-topics --max-pages 5 --delay 2.0
```

### Download Books
```bash
# Download single book
python main_downloader.py 9781098118723

# Download from file
python main_downloader.py --from-file book_lists/generative-ai_book_ids.json

# Download with custom settings
python main_downloader.py 9781098118723 --output-dir my_books --basic-epub
```

### Complete Topic Workflow
```bash
# Parse and download a topic
python main_topic_downloader.py generative-ai

# Parse and download with custom settings
python main_topic_downloader.py python --max-pages 5 --delay 1.0

# Download from existing book IDs
python main_topic_downloader.py --from-file book_lists/generative-ai_book_ids.json
```

## Output Files

### Parser Outputs
- `{topic}_complete_{timestamp}.json` - Complete book data
- `{topic}_book_ids_{timestamp}.json` - Just the book IDs
- `{topic}_summary_{timestamp}.txt` - Human-readable summary

### Downloader Outputs
- `{book_title}.epub` - Downloaded books in EPUB format
- Organized in output directory structure

## API Limitations

- **Unauthenticated users**: Limited to first 10 pages (1000 books max per topic)
- **Rate limiting**: Built-in delays to avoid rate limits
- **Authentication required**: For full access to all pages

## Requirements

- Python 3.7+
- requests
- lxml
- tqdm (optional, for progress bars)

## Installation

```bash
pip install -r requirements.txt
```

## Authentication

The toolkit supports both authenticated and unauthenticated access:

- **Authenticated**: Full access to all pages and books
- **Unauthenticated**: Limited to first 10 pages per topic

Authentication is handled automatically when possible.

## Available Topics

The parser can extract books from topics such as:

- `generative-ai` - Generative AI and LLMs
- `python` - Python programming
- `machine-learning` - Machine learning
- `data-science` - Data science
- `programming-languages` - Programming languages
- `software-development` - Software development
- `web-mobile` - Web and mobile development
- `business` - Business topics
- `security` - Security
- `cloud-computing` - Cloud computing
- And many more...

## Workflow Examples

### 1. Parse a Topic and Get Book IDs
```bash
python main_parser.py topic generative-ai
# Output: book_lists/generative-ai_book_ids_20250926_004629.json
```

### 2. Download Books from Parsed IDs
```bash
python main_downloader.py --from-file book_lists/generative-ai_book_ids_20250926_004629.json
# Output: books/*.epub files
```

### 3. Complete Topic Workflow (One Command)
```bash
python main_topic_downloader.py generative-ai
# Output: Parsed topic + Downloaded books
```

## Troubleshooting

### Authentication Issues
- Check your O'Reilly Learning credentials
- Use `--no-auth` flag for limited access
- Check the `cookies.json` file for valid session data

### Rate Limiting
- Increase the `--delay` parameter
- Reduce the `--max-pages` parameter
- Use authentication for better rate limits

### Page Limits
- Unauthenticated users are limited to 10 pages per topic
- Use authentication for full access
- The parser will automatically detect and handle page limits

## Contributing

This toolkit is designed to be modular and extensible:

- `book_downloader/` - Download functionality
- `book_parser/` - Parsing functionality
- `main_*.py` - Entry points for each functionality
- `experiments/` - Experimental features
- `archive/` - Archived files

## License

See LICENSE.md for license information.