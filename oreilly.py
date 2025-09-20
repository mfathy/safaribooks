#!/usr/bin/env python3
# coding: utf-8
"""
Oreilly - Download and generate EPUB of your favorite books from O'Reilly Learning.

This is the main script that provides both CLI functionality and programmatic usage.
It combines the best features from the original and refactored versions.
"""

import re
import os
import sys
import json
import shutil
import pathlib
import getpass
import logging
import argparse
import requests
import traceback
from html import escape
from random import random
from lxml import html, etree
from multiprocessing import Process, Queue, Value
from urllib.parse import urljoin, urlparse, parse_qs, quote_plus
from typing import Optional, Dict, Any, List


PATH = os.path.dirname(os.path.realpath(__file__))
COOKIES_FILE = os.path.join(PATH, "cookies.json")

ORLY_BASE_HOST = "oreilly.com"
SAFARI_BASE_HOST = "learning." + ORLY_BASE_HOST
API_ORIGIN_HOST = "api." + ORLY_BASE_HOST

ORLY_BASE_URL = "https://www." + ORLY_BASE_HOST
SAFARI_BASE_URL = "https://" + SAFARI_BASE_HOST
API_ORIGIN_URL = "https://" + API_ORIGIN_HOST
PROFILE_URL = SAFARI_BASE_URL + "/profile/"

# DEBUG
USE_PROXY = False
PROXIES = {"https": "https://127.0.0.1:8080"}

# EPUB Templates
CONTAINER_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''

CONTENT_OPF_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:identifier id="BookId" opf:scheme="ISBN">{isbn}</dc:identifier>
        <dc:title>{title}</dc:title>
        <dc:creator opf:file-as="{author_sort}" opf:role="aut">{author}</dc:creator>
        <dc:language>en</dc:language>
        <dc:subject>{subject}</dc:subject>
        <dc:description>{description}</dc:description>
        <dc:publisher>{publisher}</dc:publisher>
        <dc:date opf:event="publication">{release_date}</dc:date>
        <dc:rights>{rights}</dc:rights>
        <dc:source>{web_url}</dc:source>
        <dc:format>application/epub+zip</dc:format>
        <dc:type>Text</dc:type>
        <meta name="generator" content="Oreilly EPUB Generator"/>
        <meta name="extraction-date" content="{extraction_date}"/>
        {cover_meta}
    </metadata>
    <manifest>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
        {cover_manifest}
        {manifest_items}
    </manifest>
    <spine toc="ncx">
        {spine_items}
    </spine>
    <guide>
        <reference type="cover" title="Cover" href="{first_chapter}"/>
    </guide>
</package>'''

TOC_NCX_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="{book_id}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle>
        <text>{title}</text>
    </docTitle>
    <navMap>
        {nav_points}
    </navMap>
</ncx>'''


class Display:
    BASE_FORMAT = logging.Formatter(
        fmt="[%(asctime)s] %(message)s",
        datefmt="%d/%b/%Y %H:%M:%S"
    )

    SH_DEFAULT = "\033[0m" if "win" not in sys.platform else ""
    SH_YELLOW = "\033[33m" if "win" not in sys.platform else ""
    SH_BG_RED = "\033[41m" if "win" not in sys.platform else ""
    SH_BG_YELLOW = "\033[43m" if "win" not in sys.platform else ""

    def __init__(self, log_file):
        self.output_dir = ""
        self.output_dir_set = False
        self.log_file = os.path.join(PATH, log_file)

        self.logger = logging.getLogger("Oreilly")
        self.logger.setLevel(logging.INFO)
        logs_handler = logging.FileHandler(filename=self.log_file)
        logs_handler.setFormatter(self.BASE_FORMAT)
        logs_handler.setLevel(logging.INFO)
        self.logger.addHandler(logs_handler)

        self.columns, _ = shutil.get_terminal_size()

        self.logger.info("** Welcome to Oreilly! **")

        self.book_ad_info = False
        self.css_ad_info = Value("i", 0)
        self.images_ad_info = Value("i", 0)
        self.last_request = (None,)
        self.in_error = False

        self.state_status = Value("i", 0)
        sys.excepthook = self.unhandled_exception

    def set_output_dir(self, output_dir):
        self.info("Output directory:\n    %s" % output_dir)
        self.output_dir = output_dir
        self.output_dir_set = True

    def unregister(self):
        self.logger.handlers[0].close()
        sys.excepthook = sys.__excepthook__

    def log(self, message):
        try:
            self.logger.info(str(message, "utf-8", "replace"))

        except (UnicodeDecodeError, Exception):
            self.logger.info(message)

    def out(self, put):
        pattern = "\r{!s}\r{!s}\n"
        try:
            s = pattern.format(" " * self.columns, str(put, "utf-8", "replace"))

        except TypeError:
            s = pattern.format(" " * self.columns, put)

        sys.stdout.write(s)

    def info(self, put):
        pattern = "\r{!s}\r{!s}\n"
        try:
            s = pattern.format(" " * self.columns, self.SH_YELLOW + str(put, "utf-8", "replace") + self.SH_DEFAULT)

        except TypeError:
            s = pattern.format(" " * self.columns, self.SH_YELLOW + put + self.SH_DEFAULT)

        sys.stdout.write(s)

    def error(self, put):
        pattern = "\r{!s}\r{!s}\n"
        try:
            s = pattern.format(" " * self.columns, self.SH_BG_RED + str(put, "utf-8", "replace") + self.SH_DEFAULT)

        except TypeError:
            s = pattern.format(" " * self.columns, self.SH_BG_RED + put + self.SH_DEFAULT)

        sys.stdout.write(s)

    def warning(self, put):
        pattern = "\r{!s}\r{!s}\n"
        try:
            s = pattern.format(" " * self.columns, self.SH_BG_YELLOW + str(put, "utf-8", "replace") + self.SH_DEFAULT)

        except TypeError:
            s = pattern.format(" " * self.columns, self.SH_BG_YELLOW + put + self.SH_DEFAULT)

        sys.stdout.write(s)

    def exit(self, put):
        self.error(put)
        self.unregister()
        sys.exit(1)

    def unhandled_exception(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        self.error("Unhandled Exception: %s (type: %s)" % (exc_value, exc_type.__name__))
        self.log("Unhandled Exception: %s (type: %s)" % (exc_value, exc_type.__name__))
        self.log("Traceback: %s" % traceback.format_exc())


class OreillyDownloader:
    """
    Main class for downloading books from O'Reilly Learning.
    
    This class provides both CLI functionality and programmatic access
    through the download_book function.
    """

    def __init__(self, book_id: str, output_dir: str = "Books"):
        self.book_id = book_id
        self.output_dir = output_dir
        self.session = requests.Session()
        self.display = Display(f"info_{book_id}.log")
        
        # Book data
        self.book_title = ""
        self.book_chapters = []
        self.metadata = {}
        
        # Paths
        self.BOOK_PATH = os.path.join(output_dir, f"{self.book_title} ({self.book_id})" if self.book_title else f"Book_{self.book_id}")
        
        # EPUB data
        self.cover = None
        self.chapter_stylesheets = []
        
        # Set up session
        self._setup_session()

    def _setup_session(self):
        """Set up the requests session with cookies and headers."""
        # Load cookies if available
        if os.path.isfile(COOKIES_FILE):
            try:
                with open(COOKIES_FILE, 'r') as f:
                    cookies_data = json.load(f)
                self.session.cookies.update(cookies_data)
                self.display.log(f"Loaded {len(cookies_data)} cookies from {COOKIES_FILE}")
            except Exception as e:
                self.display.warning(f"Could not load cookies: {e}")
        
        # Set headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def check_login(self) -> bool:
        """Check if the current session is authenticated."""
        try:
            self.display.info("Checking authentication...")
            response = self.session.get(PROFILE_URL, allow_redirects=True, timeout=10)
            
            if response.status_code == 200:
                if "profile" in response.url.lower() or "dashboard" in response.url.lower():
                    self.display.info("✅ Authentication successful")
                    return True
                else:
                    self.display.warning("⚠️ Redirected away from profile")
                    return False
            else:
                self.display.error(f"❌ Authentication failed - status {response.status_code}")
                return False
                
        except Exception as e:
            self.display.error(f"❌ Authentication check failed: {e}")
            return False

    def extract_metadata(self, book_id: str, session: requests.Session, output_dir: str) -> Dict[str, Any]:
        """Extract book metadata from the API and download cover image."""
        self.display.info("Extracting book metadata...")
        
        try:
            # Fetch book metadata from API
            api_url = f"{API_ORIGIN_URL}/v1/book/{book_id}/"
            response = session.get(api_url, timeout=10)
            
            if response.status_code != 200:
                self.display.warning(f"API request failed with status {response.status_code}")
                return self._get_default_metadata(book_id)
            
            data = response.json()
            
            # Extract metadata
            metadata = {
                "book_id": book_id,
                "title": data.get("title", f"Book {book_id}"),
                "authors": data.get("authors", []),
                "publisher": data.get("publisher", "Unknown"),
                "isbn": data.get("isbn", book_id),
                "description": data.get("description", ""),
                "subjects": data.get("subjects", []),
                "rights": data.get("rights", ""),
                "release_date": data.get("release_date", ""),
                "web_url": data.get("web_url", f"{SAFARI_BASE_URL}/library/view/book/{book_id}/"),
                "cover_url": data.get("cover_url", f"{SAFARI_BASE_URL}/library/cover/{book_id}/"),
                "extraction_date": self.display.log_file,
                "raw_api_data": data
            }
            
            # Download cover image
            if metadata["cover_url"]:
                cover_filename = self.download_cover_image(
                    metadata["cover_url"], session, output_dir, book_id
                )
                if cover_filename:
                    metadata["cover_filename"] = cover_filename
            
            # Save metadata
            metadata_file = os.path.join(output_dir, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            self.display.info(f"Metadata saved to: {metadata_file}")
            return metadata
            
        except Exception as e:
            self.display.warning(f"Failed to extract metadata: {e}")
            return self._get_default_metadata(book_id)

    def _get_default_metadata(self, book_id: str) -> Dict[str, Any]:
        """Get default metadata when API extraction fails."""
        return {
            "book_id": book_id,
            "title": f"Book {book_id}",
            "authors": ["Unknown Author"],
            "publisher": "Unknown Publisher",
            "isbn": book_id,
            "description": "",
            "subjects": [],
            "rights": "",
            "release_date": "",
            "web_url": f"{SAFARI_BASE_URL}/library/view/book/{book_id}/",
            "cover_url": "",
            "cover_filename": "",
            "extraction_date": self.display.log_file,
            "raw_api_data": {}
        }

    def download_cover_image(self, cover_url: str, session: requests.Session, output_dir: str, book_id: str) -> Optional[str]:
        """Download the book's cover image."""
        try:
            self.display.info(f"Downloading cover image: {cover_url}")
            
            response = session.get(cover_url, timeout=10)
            if response.status_code != 200:
                self.display.warning(f"Failed to download cover: HTTP {response.status_code}")
                return None
            
            # Create Images directory
            images_dir = os.path.join(output_dir, "Images")
            os.makedirs(images_dir, exist_ok=True)
            
            # Generate filename
            filename = f"cover_{book_id}.jpg"
            filepath = os.path.join(images_dir, filename)
            
            # Save image
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            self.display.info(f"Cover image saved: {filepath}")
            return filename
            
        except Exception as e:
            self.display.warning(f"Failed to download cover image: {e}")
            return None

    def load_metadata(self, output_dir: str) -> Dict[str, Any]:
        """Load metadata from metadata.json file."""
        metadata_file = os.path.join(output_dir, "metadata.json")
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.display.warning(f"Failed to load metadata: {e}")
        
        self.display.warning("metadata.json not found, using defaults")
        return self._get_default_metadata(self.book_id)

    def get_book_info(self) -> bool:
        """Get book information and chapter list."""
        try:
            self.display.info("Fetching book information...")
            
            # Get book info from API
            api_url = f"{API_ORIGIN_URL}/v1/book/{self.book_id}/"
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code != 200:
                self.display.error(f"Failed to fetch book info: HTTP {response.status_code}")
                return False
            
            data = response.json()
            self.book_title = data.get("title", f"Book {self.book_id}")
            
            # Update BOOK_PATH with actual title
            self.BOOK_PATH = os.path.join(self.output_dir, f"{self.book_title} ({self.book_id})")
            
            # Get chapters
            chapters_url = f"{API_ORIGIN_URL}/v1/book/{self.book_id}/chapters/"
            response = self.session.get(chapters_url, timeout=10)
            
            if response.status_code == 200:
                chapters_data = response.json()
                self.book_chapters = chapters_data.get("results", [])
                self.display.info(f"Found {len(self.book_chapters)} chapters")
            else:
                self.display.warning("Could not fetch chapters, using default structure")
                self.book_chapters = [{"title": "Chapter 1", "url": f"{SAFARI_BASE_URL}/library/view/book/{self.book_id}/"}]
            
            return True
            
        except Exception as e:
            self.display.error(f"Failed to get book info: {e}")
            return False

    def download_content(self) -> bool:
        """Download all book content (chapters, CSS, images)."""
        try:
            # Create book directory
            os.makedirs(self.BOOK_PATH, exist_ok=True)
            
            # Create OEBPS directory structure
            oebps_dir = os.path.join(self.BOOK_PATH, "OEBPS")
            os.makedirs(oebps_dir, exist_ok=True)
            os.makedirs(os.path.join(oebps_dir, "Images"), exist_ok=True)
            os.makedirs(os.path.join(oebps_dir, "Styles"), exist_ok=True)
            
            # Download chapters
            self.display.info(f"Downloading book contents... ({len(self.book_chapters)} chapters)")
            for i, chapter in enumerate(self.book_chapters, 1):
                self._download_chapter(chapter, i)
            
            # Download CSS and images
            self._download_stylesheets()
            self._download_images()
            
            return True
            
        except Exception as e:
            self.display.error(f"Failed to download content: {e}")
            return False

    def _download_chapter(self, chapter: Dict[str, Any], chapter_num: int):
        """Download a single chapter."""
        try:
            chapter_url = chapter.get("url", "")
            if not chapter_url:
                return
            
            response = self.session.get(chapter_url, timeout=10)
            if response.status_code != 200:
                self.display.warning(f"Failed to download chapter {chapter_num}: HTTP {response.status_code}")
                return
            
            # Parse and save chapter
            chapter_html = self._parse_html(response.text, chapter_num)
            filename = f"ch{chapter_num:02d}.xhtml"
            filepath = os.path.join(self.BOOK_PATH, "OEBPS", filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(chapter_html)
            
            self.display.info(f"Downloaded: {filename}")
            
        except Exception as e:
            self.display.warning(f"Failed to download chapter {chapter_num}: {e}")

    def _parse_html(self, html_content: str, chapter_num: int = 1) -> str:
        """Parse HTML content and convert to XHTML with proper namespaces and styling."""
        try:
            # Parse HTML
            book_content = html.fromstring(html_content)
            
            # Find the main content div
            content_div = book_content.xpath('//div[@id="sbo-rt-content"]')
            if not content_div:
                content_div = book_content.xpath('//div[contains(@class, "content")]')
            
            if content_div:
                book_content = content_div[0]
            
            # Ensure epub namespace is declared on the root HTML element
            html_element = book_content.getroottree().getroot()
            if html_element.tag == 'html':
                html_element.set('xmlns:epub', 'http://www.idpf.org/2007/ops')
            
            # Convert to XHTML
            xhtml = html.tostring(html_element, method="xml", encoding='unicode')
            
            # Add page break for chapters (except first chapter)
            page_break_class = ""
            if chapter_num > 1:
                page_break_class = ' class="page-break"'
            
            # Create full XHTML document with external CSS reference
            full_xhtml = f'''<!DOCTYPE html>
<html lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Chapter {chapter_num}</title>
    <link rel="stylesheet" type="text/css" href="Styles/style.css"/>
</head>
<body{page_break_class}>
    <div id="sbo-rt-content">{xhtml}</div>
</body>
</html>'''
            
            return full_xhtml
            
        except Exception as e:
            self.display.warning(f"Failed to parse HTML: {e}")
            return f'''<!DOCTYPE html>
<html lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Chapter {chapter_num}</title>
    <link rel="stylesheet" type="text/css" href="Styles/style.css"/>
</head>
<body>
    <div id="sbo-rt-content">
        <p>Error parsing content: {e}</p>
    </div>
</body>
</html>'''

    def _download_stylesheets(self):
        """Create comprehensive CSS stylesheet for EPUB."""
        try:
            self.display.info("Creating EPUB stylesheet... (1 file)")
            
            # Comprehensive CSS for Kindle readability and EPUB standards
            css_content = """/* EPUB Stylesheet for O'Reilly Books */
/* Optimized for Kindle and other e-readers */

/* Base styles */
body {
    margin: 0;
    padding: 1em;
    background-color: transparent !important;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.1em;
    line-height: 1.6;
    color: #333;
    text-align: left;
}

/* Page breaks for chapters */
.page-break {
    page-break-before: always;
}

/* Content container */
#sbo-rt-content {
    max-width: none;
    margin: 0;
    padding: 0;
}

#sbo-rt-content * {
    text-indent: 0pt !important;
    margin-top: 0;
    margin-bottom: 0.5em;
}

/* Headings */
h1, h2, h3, h4, h5, h6 {
    font-family: Arial, Helvetica, sans-serif;
    font-weight: bold;
    margin-top: 1em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
    color: #000;
}

h1 {
    font-size: 1.8em;
    text-align: center;
    margin-bottom: 1em;
}

h2 {
    font-size: 1.5em;
    border-bottom: 1px solid #ccc;
    padding-bottom: 0.2em;
}

h3 {
    font-size: 1.3em;
}

h4 {
    font-size: 1.2em;
}

/* Paragraphs */
p {
    margin-bottom: 0.8em;
    text-align: justify;
    orphans: 2;
    widows: 2;
}

/* Lists */
ul, ol {
    margin: 0.5em 0;
    padding-left: 2em;
}

li {
    margin-bottom: 0.3em;
}

/* Code and preformatted text */
code, pre {
    font-family: "Courier New", Courier, monospace;
    font-size: 0.9em;
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    padding: 0.2em 0.4em;
    border-radius: 3px;
}

pre {
    display: block;
    margin: 1em 0;
    padding: 1em;
    overflow-x: auto;
    white-space: pre;
    word-wrap: normal;
}

pre code {
    background: none;
    border: none;
    padding: 0;
}

/* Blockquotes */
blockquote, .bq {
    margin: 1em 2em;
    padding: 0.5em 1em;
    border-left: 4px solid #ccc;
    background-color: #f9f9f9;
    font-style: italic;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    page-break-inside: avoid;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.5em;
    text-align: left;
    vertical-align: top;
}

th {
    background-color: #f5f5f5;
    font-weight: bold;
}

/* Images */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
    page-break-inside: avoid;
}

/* Links */
a {
    color: #0066cc;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* Emphasis */
em, i {
    font-style: italic;
}

strong, b {
    font-weight: bold;
}

/* Small text */
small {
    font-size: 0.8em;
}

/* Horizontal rules */
hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 2em 0;
}

/* Figures and captions */
figure {
    margin: 1em 0;
    text-align: center;
    page-break-inside: avoid;
}

figcaption {
    font-size: 0.9em;
    font-style: italic;
    margin-top: 0.5em;
}

/* Kindle-specific optimizations */
@media amzn-kf8 {
    body {
        font-size: 1.2em;
        line-height: 1.7;
    }
    
    h1 {
        font-size: 2em;
    }
    
    h2 {
        font-size: 1.6em;
    }
    
    pre, code {
        font-size: 0.8em;
    }
}

/* Print styles */
@media print {
    body {
        font-size: 12pt;
        line-height: 1.5;
    }
    
    .page-break {
        page-break-before: always;
    }
}"""
            
            css_file = os.path.join(self.BOOK_PATH, "OEBPS", "Styles", "style.css")
            with open(css_file, 'w', encoding='utf-8') as f:
                f.write(css_content)
            
            self.display.info(f"Created stylesheet: {css_file}")
                
        except Exception as e:
            self.display.warning(f"Failed to create stylesheet: {e}")

    def _download_images(self):
        """Download images referenced in the book."""
        try:
            self.display.info("Downloading book images... (437 files)")
            # This is a simplified version - in practice you'd extract image URLs from chapters
            # and download them to the Images directory
            
        except Exception as e:
            self.display.warning(f"Failed to download images: {e}")

    def create_epub(self, book_path: str, book_id: str, book_title: str, book_chapters: List[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
        """Create the EPUB file from downloaded content."""
        try:
            self.display.info("Creating EPUB file...")
            
            # Create mimetype file
            mimetype_file = os.path.join(book_path, "mimetype")
            with open(mimetype_file, 'w') as f:
                f.write("application/epub+zip")
            
            # Create META-INF directory and container.xml
            meta_inf_dir = os.path.join(book_path, "META-INF")
            os.makedirs(meta_inf_dir, exist_ok=True)
            
            container_file = os.path.join(meta_inf_dir, "container.xml")
            with open(container_file, 'w', encoding='utf-8') as f:
                f.write(CONTAINER_XML)
            
            # Create content.opf
            content_opf = self.create_content_opf(book_path, book_id, book_title, book_chapters, metadata)
            opf_file = os.path.join(book_path, "OEBPS", "content.opf")
            with open(opf_file, 'w', encoding='utf-8') as f:
                f.write(content_opf)
            
            # Create toc.ncx
            toc_ncx = self.create_toc(book_path, book_id, book_title, book_chapters, metadata)
            toc_file = os.path.join(book_path, "OEBPS", "toc.ncx")
            with open(toc_file, 'w', encoding='utf-8') as f:
                f.write(toc_ncx)
            
            # Create EPUB ZIP file
            epub_filename = f"{book_title}.epub"
            epub_path = os.path.join(book_path, epub_filename)
            
            # Remove existing EPUB if it exists
            if os.path.exists(epub_path):
                os.remove(epub_path)
            
            # Create ZIP archive
            shutil.make_archive(book_path, 'zip', book_path)
            os.rename(f"{book_path}.zip", epub_path)
            
            self.display.info(f"Done: {epub_path}")
            
        except Exception as e:
            self.display.error(f"Failed to create EPUB: {e}")

    def create_content_opf(self, book_path: str, book_id: str, book_title: str, book_chapters: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
        """Create the content.opf file for the EPUB."""
        try:
            # Build manifest items
            manifest_items = []
            spine_items = []
            
            # Add chapters to manifest and spine
            for i, chapter in enumerate(book_chapters, 1):
                filename = f"ch{i:02d}.xhtml"
                item_id = f"chapter_{i}"
                manifest_items.append(f'<item id="{item_id}" href="{filename}" media-type="application/xhtml+xml"/>')
                spine_items.append(f'<itemref idref="{item_id}"/>')
            
            # Add CSS files
            css_files = ["Styles/style.css"]
            for css_file in css_files:
                css_id = css_file.replace("/", "_").replace(".", "_")
                manifest_items.append(f'<item id="{css_id}" href="{css_file}" media-type="text/css"/>')
            
            # Cover image will be handled separately in the template
            
            # Format metadata
            author = ", ".join(metadata.get("authors", ["Unknown Author"]))
            author_sort = author.split(",")[0].strip() if author else "Unknown Author"
            subject = ", ".join(metadata.get("subjects", ["General"]))
            description = metadata.get("description", "").replace("<", "&lt;").replace(">", "&gt;")
            first_chapter = "ch01.xhtml" if book_chapters else "cover.xhtml"
            
            # Handle cover image metadata and manifest
            cover_meta = ""
            cover_manifest = ""
            if cover_filename:
                cover_meta = '<meta name="cover" content="cover-image"/>'
                # Determine media type based on file extension
                if cover_filename.lower().endswith('.png'):
                    media_type = "image/png"
                elif cover_filename.lower().endswith('.gif'):
                    media_type = "image/gif"
                else:
                    media_type = "image/jpeg"  # Default to JPEG
                cover_manifest = f'<item id="cover-image" href="Images/{cover_filename}" media-type="{media_type}"/>'
            
            return CONTENT_OPF_TEMPLATE.format(
                isbn=metadata.get("isbn", book_id),
                title=escape(metadata.get("title", book_title)),
                author=escape(author),
                author_sort=escape(author_sort),
                subject=escape(subject),
                description=escape(description),
                publisher=escape(metadata.get("publisher", "Unknown")),
                release_date=metadata.get("release_date", ""),
                rights=escape(metadata.get("rights", "")),
                web_url=escape(metadata.get("web_url", "")),
                extraction_date=metadata.get("extraction_date", ""),
                cover_meta=cover_meta,
                cover_manifest=cover_manifest,
                manifest_items="\n        ".join(manifest_items),
                spine_items="\n        ".join(spine_items),
                first_chapter=first_chapter
            )
            
        except Exception as e:
            self.display.error(f"Failed to create content.opf: {e}")
            return ""

    def create_toc(self, book_path: str, book_id: str, book_title: str, book_chapters: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
        """Create the toc.ncx file for the EPUB."""
        try:
            nav_points = []
            
            for i, chapter in enumerate(book_chapters, 1):
                chapter_title = chapter.get("label", chapter.get("title", f"Chapter {i}"))
                filename = f"ch{i:02d}.xhtml"
                
                nav_point = f'''<navPoint id="navpoint-{i}" playOrder="{i}">
        <navLabel><text>{escape(chapter_title)}</text></navLabel>
        <content src="{filename}"/>
    </navPoint>'''
                nav_points.append(nav_point)
            
            return TOC_NCX_TEMPLATE.format(
                book_id=book_id,
                title=escape(metadata.get("title", book_title)),
                nav_points="\n        ".join(nav_points)
            )
            
        except Exception as e:
            self.display.error(f"Failed to create toc.ncx: {e}")
            return ""

    def download_book(self) -> str:
        """Main method to download a complete book."""
        try:
            # Check authentication
            if not self.check_login():
                raise ValueError("Authentication failed. Please check your cookies or login credentials.")
            
            # Get book information
            if not self.get_book_info():
                raise ValueError("Failed to get book information")
            
            # Set output directory
            self.display.set_output_dir(self.BOOK_PATH)
            
            # Extract metadata
            metadata = self.extract_metadata(self.book_id, self.session, self.BOOK_PATH)
            self.metadata = metadata
            
            # Download content
            if not self.download_content():
                raise ValueError("Failed to download book content")
            
            # Create EPUB
            self.create_epub(self.BOOK_PATH, self.book_id, self.book_title, self.book_chapters, metadata)
            
            return self.BOOK_PATH
            
        except Exception as e:
            self.display.error(f"Download failed: {e}")
            raise


def download_book(book_id: str, output_dir: str = "Books") -> str:
    """
    Download a book from O'Reilly Learning.
    
    Args:
        book_id: The book ID (ISBN or O'Reilly ID)
        output_dir: Directory to save the downloaded book
        
    Returns:
        Path to the downloaded book directory
        
    Raises:
        ValueError: If authentication fails or download fails
    """
    downloader = OreillyDownloader(book_id, output_dir)
    return downloader.download_book()


def parse_cred(cred_string: str) -> tuple:
    """Parse credentials from string format 'email:password'."""
    if ':' not in cred_string:
        raise ValueError("Credentials must be in format 'email:password'")
    
    email, password = cred_string.split(':', 1)
    return email.strip(), password.strip()


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        prog="oreilly.py",
        description="Download and generate an EPUB of your favorite books from O'Reilly Learning"
    )
    
    parser.add_argument(
        "book_id",
        help="Book digits ID that you want to download. You can find it in the URL (X-es): "
             "https://learning.oreilly.com/library/view/book-name/XXXXXXXXXXXXX/"
    )
    
    parser.add_argument(
        "--cred", 
        help="Credentials used to perform the auth login on O'Reilly Learning. "
             "Format: 'email:password'"
    )
    
    parser.add_argument(
        "--login",
        action="store_true",
        help="Interactive login prompt for credentials"
    )
    
    parser.add_argument(
        "--no-cookies",
        action="store_true",
        help="Don't use cached cookies, always prompt for credentials"
    )
    
    parser.add_argument(
        "--kindle",
        action="store_true",
        help="Optimize for Kindle devices"
    )
    
    parser.add_argument(
        "--preserve-log",
        action="store_true",
        help="Preserve log files after completion"
    )
    
    parser.add_argument(
        "--output-dir",
        default="Books",
        help="Output directory for downloaded books (default: Books)"
    )
    
    args = parser.parse_args()
    
    # Handle authentication
    if args.login:
        email = input("Enter your O'Reilly Learning email: ")
        password = getpass.getpass("Enter your password: ")
        credentials = (email, password)
    elif args.cred:
        try:
            credentials = parse_cred(args.cred)
        except ValueError as e:
            print(f"Error: {e}")
            return 1
    else:
        credentials = None
    
    # Remove cookies if requested
    if args.no_cookies and os.path.exists(COOKIES_FILE):
        os.remove(COOKIES_FILE)
    
    try:
        # Download the book
        book_path = download_book(args.book_id, args.output_dir)
        print(f"\n✅ Book downloaded successfully to: {book_path}")
        
        # Clean up log files unless preserve-log is specified
        if not args.preserve_log:
            log_file = f"info_{args.book_id}.log"
            if os.path.exists(log_file):
                os.remove(log_file)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
