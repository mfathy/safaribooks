#!/usr/bin/env python3
# coding: utf-8
"""
SafariBooks - Main Controller
Orchestrates the book downloading process using modular components
"""

import os
import sys
import argparse
from html import escape

# Import our modular components
from display import Display
from auth import AuthManager
from download import BookDownloader
from epub import EpubGenerator
from epub_enhanced import EnhancedEpubGenerator
from config import PATH, SAFARI_BASE_URL, BASE_01_HTML, KINDLE_HTML, BASE_02_HTML


class SafariBooks:
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
        self.epub_generator = EpubGenerator(
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
        
        # Step 8: Save cookies and cleanup
        if not self.args.no_cookies:
            self.auth_manager.save_cookies()
        
        # Step 9: Finalize
        self.display.info("EPUB generation completed successfully!")
        self.display.unregister()
        
        if not self.display.in_error and not self.args.log:
            os.remove(self.display.log_file)
    
    def _setup_book_paths(self):
        """Set up book directory structure and paths"""
        self.book_downloader.book_title = self.book_info["title"]
        self.book_downloader.base_url = self.book_info["web_url"]
        
        clean_book_title = "".join(self._escape_dirname(self.book_info["title"]).split(",")[:2]) \
                          + " ({0})".format(self.args.bookid)
        
        books_dir = os.path.join(PATH, "Books")
        if not os.path.isdir(books_dir):
            os.mkdir(books_dir)
        
        self.book_downloader.BOOK_PATH = os.path.join(books_dir, clean_book_title)
        self.display.set_output_dir(self.book_downloader.BOOK_PATH)
        
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories for the book"""
        if os.path.isdir(self.book_downloader.BOOK_PATH):
            self.display.log("Book directory already exists: %s" % self.book_downloader.BOOK_PATH)
        else:
            os.makedirs(self.book_downloader.BOOK_PATH)
        
        oebps = os.path.join(self.book_downloader.BOOK_PATH, "OEBPS")
        if not os.path.isdir(oebps):
            self.display.book_ad_info = True
            os.makedirs(oebps)
        
        self.book_downloader.css_path = os.path.join(oebps, "Styles")
        if os.path.isdir(self.book_downloader.css_path):
            self.display.log("CSSs directory already exists: %s" % self.book_downloader.css_path)
        else:
            os.makedirs(self.book_downloader.css_path)
            self.display.css_ad_info.value = 1
        
        self.book_downloader.images_path = os.path.join(oebps, "Images")
        if os.path.isdir(self.book_downloader.images_path):
            self.display.log("Images directory already exists: %s" % self.book_downloader.images_path)
        else:
            os.makedirs(self.book_downloader.images_path)
            self.display.images_ad_info.value = 1
    
    def _download_book_content(self):
        """Download all book content including chapters, CSS, and images"""
        chapters_queue = self.book_chapters[:]
        
        if len(self.book_chapters) > sys.getrecursionlimit():
            sys.setrecursionlimit(len(self.book_chapters))
        
        # Prepare HTML template
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
            if dirname.index(":") > 15:
                dirname = dirname.split(":")[0]
            elif "win" in sys.platform:
                dirname = dirname.replace(":", ",")
        
        for ch in ['~', '#', '%', '&', '*', '{', '}', '\\', '<', '>', '?', '/', '`', '\'', '"', '|', '+', ':']:
            if ch in dirname:
                dirname = dirname.replace(ch, "_")
        
        return dirname if not clean_space else dirname.replace(" ", "")


def main():
    """Main entry point"""
    arguments = argparse.ArgumentParser(prog="safaribooks.py",
                                        description="Download and generate an EPUB of your favorite books"
                                                    " from Safari Books Online.",
                                        add_help=False,
                                        allow_abbrev=False)
    
    login_arg_group = arguments.add_mutually_exclusive_group()
    login_arg_group.add_argument(
        "--cred", metavar="<EMAIL:PASS>", default=False,
        help="Credentials used to perform the auth login on Safari Books Online."
             " Es. ` --cred \"account_mail@mail.com:password01\" `."
    )
    login_arg_group.add_argument(
        "--login", action='store_true',
        help="Prompt for credentials used to perform the auth login on Safari Books Online."
    )
    
    arguments.add_argument(
        "--no-cookies", dest="no_cookies", action='store_true',
        help="Prevent your session data to be saved into `cookies.json` file."
    )
    arguments.add_argument(
        "--kindle", dest="kindle", action='store_true',
        help="Generate Kindle-optimized EPUB with enhanced formatting."
    )
    arguments.add_argument(
        "--enhanced", dest="enhanced", action='store_true',
        help="Generate enhanced EPUB 3.3 with improved metadata and formatting."
    )
    arguments.add_argument(
        "--dual", dest="dual", action='store_true',
        help="Generate both standard and Kindle-optimized EPUB files."
    )
    arguments.add_argument(
        "--preserve-log", dest="log", action='store_true', help="Leave the `info_XXXXXXXXXXXXX.log`"
                                                                " file even if there isn't any error."
    )
    arguments.add_argument("--help", action="help", default=argparse.SUPPRESS, help='Show this help message.')
    arguments.add_argument(
        "bookid", metavar='<BOOK ID>',
        help="Book digits ID that you want to download. You can find it in the URL (X-es):"
             f" `{SAFARI_BASE_URL}/library/view/book-name/XXXXXXXXXXXXX/`"
    )
    
    args_parsed = arguments.parse_args()
    
    if args_parsed.cred or args_parsed.login:
        print("WARNING: Due to recent changes on ORLY website, \n" \
                "the `--cred` and `--login` options are temporarily disabled.\n"
                "    Please use the `cookies.json` file to authenticate your account.\n"
                "    See: https://github.com/lorenzodifuccia/safaribooks/issues/358")
        arguments.exit()
    else:
        if args_parsed.no_cookies:
            arguments.error("invalid option: `--no-cookies` is valid only if you use the `--cred` option")
    
    SafariBooks(args_parsed)
    sys.exit(0)


if __name__ == "__main__":
    main()