#!/usr/bin/env python3
# coding: utf-8
"""
Refactored SafariBooks - Main Orchestrator
Uses modular components for authentication, downloading, and EPUB generation
"""

import os
import sys
import argparse
import getpass
from html import escape

# Import our modular components
from auth_manager import AuthManager
from book_downloader import BookDownloader
from epub_generator import EpubGenerator

# Import Display class from original file (we'll need to extract this too)
from safaribooks import Display

# Constants
PATH = os.path.dirname(os.path.realpath(__file__))
COOKIES_FILE = os.path.join(PATH, "cookies.json")
SAFARI_BASE_URL = "https://learning.oreilly.com"


class SafariBooksRefactored:
    """Main orchestrator class that coordinates all modules"""
    
    # HTML Templates
    BASE_01_HTML = "<!DOCTYPE html>\n" \
                   "<html lang=\"en\" xml:lang=\"en\" xmlns=\"http://www.w3.org/1999/xhtml\"" \
                   " xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"" \
                   " xsi:schemaLocation=\"http://www.w3.org/2002/06/xhtml2/" \
                   " http://www.w3.org/MarkUp/SCHEMA/xhtml2.xsd\"" \
                   " xmlns:epub=\"http://www.idpf.org/2007/ops\">\n" \
                   "<head>\n" \
                   "{0}\n" \
                   "<style type=\"text/css\">" \
                   "body{{margin:1em;background-color:transparent!important;}}" \
                   "#sbo-rt-content *{{text-indent:0pt!important;}}#sbo-rt-content .bq{{margin-right:1em!important;}}"
    
    KINDLE_HTML = "#sbo-rt-content *{{word-wrap:break-word!important;" \
                  "word-break:break-word!important;}}#sbo-rt-content table,#sbo-rt-content pre" \
                  "{{overflow-x:unset!important;overflow:unset!important;" \
                  "overflow-y:unset!important;white-space:pre-wrap!important;}}"
    
    BASE_02_HTML = "</style>" \
                   "</head>\n" \
                   "<body>{1}</body>\n</html>"
    
    def __init__(self, args):
        self.args = args
        self.display = Display("info_%s.log" % escape(args.bookid))
        self.display.intro()
        
        # Initialize modules
        self.auth_manager = AuthManager(COOKIES_FILE, self.display)
        self.book_downloader = BookDownloader(None, self.display, args.bookid)  # Session will be set later
        self.epub_generator = None  # Will be initialized after book info is retrieved
        
        # Initialize session
        self.session = self.auth_manager.initialize_session(args.cred, args.no_cookies)
        self.book_downloader.session = self.session  # Set session for downloader
        
        # Get book information
        self.display.info("Retrieving book info...")
        self.book_info = self.book_downloader.get_book_info()
        self.display.book_info(self.book_info)
        
        # Get book chapters
        self.display.info("Retrieving book chapters...")
        self.book_chapters = self.book_downloader.get_book_chapters()
        
        # Set up book paths and directories
        self._setup_book_paths()
        
        # Initialize EPUB generator
        self.epub_generator = EpubGenerator(
            self.session, self.display, self.book_info, self.book_chapters,
            self.book_downloader.BOOK_PATH, self.book_downloader.css_path, 
            self.book_downloader.images_path
        )
        
        # Download book content
        self._download_book_content()
        
        # Generate EPUB
        self._generate_epub()
        
        # Save cookies and cleanup
        if not args.no_cookies:
            self.auth_manager.save_cookies()
        
        self.display.done(os.path.join(self.book_downloader.BOOK_PATH, args.bookid + ".epub"))
        self.display.unregister()
        
        if not self.display.in_error and not args.log:
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
        base_html = self.BASE_01_HTML + (self.KINDLE_HTML if not self.args.kindle else "") + self.BASE_02_HTML
        
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
        """Generate the final EPUB file"""
        self.display.info("Creating EPUB file...", state=True)
        api_url = f"{SAFARI_BASE_URL}/api/v1/book/{self.args.bookid}/"
        self.epub_generator.create_epub(api_url, self.args.bookid, PATH)
    
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
    arguments = argparse.ArgumentParser(prog="safaribooks_refactored.py",
                                        description="Download and generate an EPUB of your favorite books"
                                                    " from Safari Books Online (Refactored Version).",
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
        help="Add some CSS rules that block overflow on `table` and `pre` elements."
             " Use this option if you're going to export the EPUB to E-Readers like Amazon Kindle."
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
    
    SafariBooksRefactored(args_parsed)
    sys.exit(0)


if __name__ == "__main__":
    main()
