#!/usr/bin/env python3
# coding: utf-8
"""
OreillyBooks - Main Controller
Orchestrates the book downloading process using modular components
"""

import os
import sys
import argparse
from html import escape

# Import our modular components
from .display import Display
from .auth import AuthManager
from .download import BookDownloader
from .epub_legacy import LegacyEpubGenerator
from .epub_enhanced import EnhancedEpubGenerator
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PATH, SAFARI_BASE_URL, BASE_01_HTML, KINDLE_HTML, BASE_02_HTML


class OreillyBooks:
    """Main controller class that orchestrates the entire process"""
    
    def __init__(self, args):
        self.args = args
        
        # Initialize display
        self.display = Display("info_%s.log" % escape(args.bookid), PATH)
        self.display.intro()
        
        # Initialize modules
        self.auth_manager = AuthManager(self.display)
        self.book_downloader = BookDownloader(None, self.display, args.bookid)
        self.epub_generator = None
        self.enhanced_epub_generator = None
        
        # Execute the main process
        self._run_process()
    
    def _run_process(self):
        """Execute the main book downloading process"""
        # Step 1: Initialize session
        self.display.info("Initializing authentication...")
        self.session = self.auth_manager.initialize_session(self.args.cred, self.args.no_cookies)
        self.book_downloader.session = self.session
        
        # Step 2: Get book information
        self.display.info("Retrieving book info...")
        self.book_info = self.book_downloader.get_book_info()
        self.display.book_info(self.book_info)
        
        # Step 3: Get book chapters
        self.display.info("Retrieving book chapters...")
        self.book_chapters = self.book_downloader.get_book_chapters()
        
        # Step 4: Set up directories
        self.display.info("Setting up book directories...")
        self._setup_book_paths()
        
        # Step 5: Initialize EPUB generators
        self.epub_generator = LegacyEpubGenerator(
            self.session, self.display, self.book_info, self.book_chapters,
            self.book_downloader.BOOK_PATH, self.book_downloader.css_path, 
            self.book_downloader.images_path
        )
        
        self.enhanced_epub_generator = EnhancedEpubGenerator(
            self.session, self.display, self.book_info, self.book_chapters,
            self.book_downloader.BOOK_PATH, self.book_downloader.css_path, 
            self.book_downloader.images_path
        )
        
        # Step 6: Download book content
        self.display.info("Starting content download...")
        self._download_book_content()
        
        # Step 7: Generate EPUB
        self.display.info("Generating EPUB file...")
        self._generate_epub()
        
        self.display.info("EPUB generation completed successfully!")
    
    def _setup_book_paths(self):
        """Set up directory structure for the book"""
        # Create book directory
        book_title = self._escape_dirname(self.book_info.get("title", "Unknown Book"))
        book_id = self.args.bookid
        
        # Check if custom output path is set (for skill-based organization)
        output_base = os.environ.get('OREILLY_OUTPUT_PATH', PATH)
        self.book_downloader.BOOK_PATH = os.path.join(output_base, "Books", f"{book_title} ({book_id})")
        
        # Create subdirectories
        os.makedirs(self.book_downloader.BOOK_PATH, exist_ok=True)
        os.makedirs(os.path.join(self.book_downloader.BOOK_PATH, "OEBPS"), exist_ok=True)
        os.makedirs(os.path.join(self.book_downloader.BOOK_PATH, "OEBPS", "Images"), exist_ok=True)
        os.makedirs(os.path.join(self.book_downloader.BOOK_PATH, "OEBPS", "Styles"), exist_ok=True)
        
        # Set paths
        self.book_downloader.css_path = os.path.join(self.book_downloader.BOOK_PATH, "OEBPS", "Styles")
        self.book_downloader.images_path = os.path.join(self.book_downloader.BOOK_PATH, "OEBPS", "Images")
        
        self.display.info("Output directory:")
        self.display.info(f"    {self.book_downloader.BOOK_PATH}")
    
    def _download_book_content(self):
        """Download all book content (chapters, CSS, images)"""
        # Prepare for chapter download
        chapters_queue = self.book_chapters[:]
        
        if len(self.book_chapters) > sys.getrecursionlimit():
            sys.setrecursionlimit(len(self.book_chapters))
        
        base_html = BASE_01_HTML + (KINDLE_HTML if not self.args.kindle else "") + BASE_02_HTML
        
        self.display.info("Downloading book contents... (%s chapters)" % len(self.book_chapters), state=True)
        
        # Download chapters
        self.book_downloader.download_chapters(chapters_queue, base_html)
        
        # Handle cover if not found
        if not self.book_downloader.cover:
            self.book_downloader.cover = self.book_downloader.get_default_cover() if "cover" in self.book_info else False
            if self.book_downloader.cover:
                from lxml import html
                cover_html = self.book_downloader.parse_html(
                    html.fromstring("<div id=\"sbo-rt-content\"><img src=\"Images/{0}\"></div>".format(self.book_downloader.cover)), True
                )
                
                self.book_chapters = [{
                    "filename": "default_cover.xhtml",
                    "title": "Cover"
                }] + self.book_chapters
                
                self.book_downloader.filename = self.book_chapters[0]["filename"]
                self.book_downloader.save_page_html(cover_html, base_html)
        
        # Download CSS files
        self.display.info("Downloading book CSSs... (%s files)" % len(self.book_downloader.css), state=True)
        self.epub_generator.collect_css(self.book_downloader.css)
        
        # Download images
        self.display.info("Downloading book images... (%s files)" % len(self.book_downloader.images), state=True)
        self.epub_generator.collect_images(self.book_downloader.images)
    
    def _generate_epub(self):
        """Generate EPUB files based on options"""
        api_url = f"{SAFARI_BASE_URL}/api/v1/book/{self.args.bookid}/"
        generated_files = []
        
        if self.args.dual:
            # Generate both versions
            self.display.info("Creating dual EPUB files (Standard + Kindle)...", state=True)
            
            self.display.info("Generating standard EPUB 3.3...")
            standard_epub = self.enhanced_epub_generator.create_enhanced_epub(api_url, self.args.bookid, PATH, is_kindle=False)
            generated_files.append(standard_epub)
            
            self.display.info("Generating Kindle-optimized EPUB...")
            kindle_epub = self.enhanced_epub_generator.create_enhanced_epub(api_url, self.args.bookid, PATH, is_kindle=True)
            generated_files.append(kindle_epub)
            
        elif self.args.enhanced or self.args.kindle:
            # Generate enhanced version
            self.display.info("Creating enhanced EPUB file...", state=True)
            is_kindle = self.args.kindle
            epub_type = "Kindle-optimized" if is_kindle else "Standard"
            
            self.display.info(f"Generating {epub_type} EPUB 3.3...")
            enhanced_epub = self.enhanced_epub_generator.create_enhanced_epub(api_url, self.args.bookid, PATH, is_kindle=is_kindle)
            generated_files.append(enhanced_epub)
            
        else:
            # Generate legacy EPUB 2.0
            self.display.info("Creating legacy EPUB file...", state=True)
            self.epub_generator.create_epub(api_url, self.args.bookid, PATH)
            generated_files.append(os.path.join(self.book_downloader.BOOK_PATH, self.args.bookid + ".epub"))
        
        # Display generated files
        if generated_files:
            self.display.info("Generated files:")
            for file_path in generated_files:
                self.display.info(f"  {os.path.basename(file_path)}")
    
    @staticmethod
    def _escape_dirname(dirname, clean_space=False):
        """Escape directory name for filesystem compatibility"""
        if ":" in dirname:
            if "win" in sys.platform:
                dirname = dirname.replace(":", ",")
            else:
                dirname = dirname.split(":")[0]
        elif "win" in sys.platform:
            dirname = dirname.replace(":", ",")
        
        for ch in ['~', '#', '%', '&', '*', '{', '}', '\\', '<', '>', '?', '/', '`', '\'', '"', '|', '+', ':']:
            if ch in dirname:
                dirname = dirname.replace(ch, "_")
        
        return dirname if not clean_space else dirname.replace(" ", "")
