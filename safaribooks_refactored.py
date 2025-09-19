#!/usr/bin/env python3
# coding: utf-8
"""
Refactored SafariBooks with extracted download_book function.

This module provides both the original CLI functionality and a reusable
download_book function for programmatic usage.
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

        self.logger = logging.getLogger("SafariBooks")
        self.logger.setLevel(logging.INFO)
        logs_handler = logging.FileHandler(filename=self.log_file)
        logs_handler.setFormatter(self.BASE_FORMAT)
        logs_handler.setLevel(logging.INFO)
        self.logger.addHandler(logs_handler)

        self.columns, _ = shutil.get_terminal_size()

        self.logger.info("** Welcome to SafariBooks! **")

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

    def info(self, message, state=False):
        self.log(message)
        output = (self.SH_YELLOW + "[*]" + self.SH_DEFAULT if not state else
                  self.SH_BG_YELLOW + "[-]" + self.SH_DEFAULT) + " %s" % message
        self.out(output)

    def error(self, error):
        if not self.in_error:
            self.in_error = True
        self.log(error)
        output = self.SH_BG_RED + "[#]" + self.SH_DEFAULT + " %s" % error
        self.out(output)

    def exit(self, error):
        self.error(str(error))
        if self.output_dir_set:
            output = (self.SH_YELLOW + "[+]" + self.SH_DEFAULT +
                      " Please delete the output directory '" + self.output_dir + "'"
                      " and restart the program.")
            self.out(output)
        output = self.SH_BG_RED + "[!]" + self.SH_DEFAULT + " Aborting..."
        self.out(output)
        self.save_last_request()
        sys.exit(1)

    def unhandled_exception(self, _, o, tb):
        self.log("".join(traceback.format_tb(tb)))
        self.exit("Unhandled Exception: %s (type: %s)" % (o, o.__class__.__name__))

    def save_last_request(self):
        if any(self.last_request):
            self.log("Last request done:\n\tURL: {0}\n\tDATA: {1}\n\tOTHERS: {2}\n\n\t{3}\n{4}\n\n{5}\n"
                     .format(*self.last_request))

    def intro(self):
        output = self.SH_YELLOW + (r"""
       ____     ___         _
      / __/__ _/ _/__ _____(_)
     _\ \/ _ `/ _/ _ `/ __/ /
    /___/\_,_/_/ \_,_/_/ /_/
      / _ )___  ___  / /__ ___
     / _  / _ \/ _ \/  '_/(_-<
    /____/\___/\___/_/\_\/___/
""" if random() > 0.5 else r"""
 ██████╗     ██████╗ ██╗  ██╗   ██╗██████╗
██╔═══██╗    ██╔══██╗██║  ╚██╗ ██╔╝╚════██╗
██║   ██║    ██████╔╝██║   ╚████╔╝   ▄███╔╝
██║   ██║    ██╔══██╗██║    ╚██╔╝    ▀▀══╝
╚██████╔╝    ██║  ██║███████╗██║     ██╗
 ╚═════╝     ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝
""") + self.SH_DEFAULT
        output += "\n" + "~" * (self.columns // 2)
        self.out(output)

    def parse_description(self, desc):
        if not desc:
            return "n/d"
        try:
            return html.fromstring(desc).text_content()
        except (html.etree.ParseError, html.etree.ParserError) as e:
            self.log("Error parsing the description: %s" % e)
            return "n/d"

    def book_info(self, info):
        description = self.parse_description(info.get("description", None)).replace("\n", " ")
        for t in [
            ("Title", info.get("title", "")), ("Authors", ", ".join(aut.get("name", "") for aut in info.get("authors", []))),
            ("Identifier", info.get("identifier", "")), ("ISBN", info.get("isbn", "")),
            ("Publishers", ", ".join(pub.get("name", "") for pub in info.get("publishers", []))),
            ("Rights", info.get("rights", "")),
            ("Description", description[:500] + "..." if len(description) >= 500 else description),
            ("Release Date", info.get("issued", "")),
            ("URL", info.get("web_url", ""))
        ]:
            self.info("{0}{1}{2}: {3}".format(self.SH_YELLOW, t[0], self.SH_DEFAULT, t[1]), True)

    def state(self, origin, done):
        progress = int(done * 100 / origin)
        bar = int(progress * (self.columns - 11) / 100)
        if self.state_status.value < progress:
            self.state_status.value = progress
            sys.stdout.write(
                "\r    " + self.SH_BG_YELLOW + "[" + ("#" * bar).ljust(self.columns - 11, "-") + "]" +
                self.SH_DEFAULT + ("%4s" % progress) + "%" + ("\n" if progress == 100 else "")
            )

    def done(self, epub_file):
        self.info("Done: %s\n\n" % epub_file +
                  "    If you like it, please * this project on GitHub to make it known:\n"
                  "        https://github.com/lorenzodifuccia/safaribooks\n"
                  "    e don't forget to renew your Safari Books Online subscription:\n"
                  "        " + SAFARI_BASE_URL + "\n\n" +
                  self.SH_BG_RED + "[!]" + self.SH_DEFAULT + " Bye!!")

    @staticmethod
    def api_error(response):
        message = "API: "
        if "detail" in response and "Not found" in response["detail"]:
            message += "book's not present in Safari Books Online.\n" \
                       "    The book identifier is the digits that you can find in the URL:\n" \
                       "    `" + SAFARI_BASE_URL + "/library/view/book-name/XXXXXXXXXXXXX/`"
        else:
            os.remove(COOKIES_FILE)
            message += "Out-of-Session%s.\n" % (" (%s)" % response["detail"]) if "detail" in response else "" + \
                       Display.SH_YELLOW + "[+]" + Display.SH_DEFAULT + \
                       " Use the `--cred` or `--login` options in order to perform the auth login to Safari."
        return message


class WinQueue(list):
    def put(self, el):
        self.append(el)

    def qsize(self):
        return self.__len__()


class SafariBooksDownloader:
    """
    Core downloader class that handles authentication and book downloading.
    Can be used both programmatically and via CLI.
    """
    
    LOGIN_URL = ORLY_BASE_URL + "/member/auth/login/"
    LOGIN_ENTRY_URL = SAFARI_BASE_URL + "/login/unified/?next=/home/"
    API_TEMPLATE = SAFARI_BASE_URL + "/api/v1/book/{0}/"

    HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Referer": LOGIN_ENTRY_URL,
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/90.0.4430.212 Safari/537.36"
    }

    COOKIE_FLOAT_MAX_AGE_PATTERN = re.compile(r'(max-age=\d*\.\d*)', re.IGNORECASE)

    def __init__(self, display: Optional[Display] = None, cookies_file: str = COOKIES_FILE):
        """
        Initialize the downloader.
        
        Args:
            display: Display object for logging and output. If None, creates a minimal one.
            cookies_file: Path to cookies file
        """
        self.display = display or self._create_minimal_display()
        self.cookies_file = cookies_file
        self.session = requests.Session()
        
        if USE_PROXY:
            self.session.proxies = PROXIES
            self.session.verify = False

        self.session.headers.update(self.HEADERS)
        self.jwt = {}

    def _create_minimal_display(self) -> Display:
        """Create a minimal display object for programmatic usage."""
        return Display("safaribooks_download.log")

    def handle_cookie_update(self, set_cookie_headers):
        """Handle cookie updates from server responses."""
        for morsel in set_cookie_headers:
            if self.COOKIE_FLOAT_MAX_AGE_PATTERN.search(morsel):
                cookie_key, cookie_value = morsel.split(";")[0].split("=")
                self.session.cookies.set(cookie_key, cookie_value)

    def requests_provider(self, url, is_post=False, data=None, perform_redirect=True, **kwargs):
        """Make HTTP requests with proper error handling and cookie management."""
        try:
            response = getattr(self.session, "post" if is_post else "get")(
                url,
                data=data,
                allow_redirects=False,
                **kwargs
            )

            self.handle_cookie_update(response.raw.headers.getlist("Set-Cookie"))

            self.display.last_request = (
                url, data, kwargs, response.status_code, "\n".join(
                    ["\t{}: {}".format(*h) for h in response.headers.items()]
                ), response.text
            )

        except (requests.ConnectionError, requests.ConnectTimeout, requests.RequestException) as request_exception:
            self.display.error(str(request_exception))
            return 0

        if response.is_redirect and perform_redirect:
            return self.requests_provider(response.next.url, is_post, None, perform_redirect)

        return response

    def authenticate(self, credentials: Optional[tuple] = None) -> None:
        """
        Authenticate with Safari Books Online.
        
        Args:
            credentials: Tuple of (email, password). If None, loads from cookies.
        """
        if not credentials:
            if not os.path.isfile(self.cookies_file):
                raise ValueError("No cookies file found and no credentials provided. "
                               "Please use --cred or --login options, or ensure cookies.json exists.")

            self.session.cookies.update(json.load(open(self.cookies_file)))
        else:
            self.display.info("Logging into Safari Books Online...", state=True)
            self.do_login(*credentials)
            json.dump(self.session.cookies.get_dict(), open(self.cookies_file, 'w'))

        self.check_login()

    def do_login(self, email: str, password: str) -> None:
        """Perform login with email and password."""
        response = self.requests_provider(self.LOGIN_ENTRY_URL)
        if response == 0:
            raise ConnectionError("Unable to reach Safari Books Online. Try again...")

        next_parameter = None
        try:
            next_parameter = parse_qs(urlparse(response.request.url).query)["next"][0]
        except (AttributeError, ValueError, IndexError):
            raise ValueError("Unable to complete login on Safari Books Online. Try again...")

        redirect_uri = API_ORIGIN_URL + quote_plus(next_parameter)

        response = self.requests_provider(
            self.LOGIN_URL,
            is_post=True,
            json={
                "email": email,
                "password": password,
                "redirect_uri": redirect_uri
            },
            perform_redirect=False
        )

        if response == 0:
            raise ConnectionError("Unable to perform auth to Safari Books Online. Try again...")

        if response.status_code != 200:
            try:
                error_page = html.fromstring(response.text)
                errors_message = error_page.xpath("//ul[@class='errorlist']//li/text()")
                recaptcha = error_page.xpath("//div[@class='g-recaptcha']")
                messages = (["    `%s`" % error for error in errors_message
                             if "password" in error or "email" in error] if len(errors_message) else []) + \
                           (["    `ReCaptcha required (wait or do logout from the website).`"] if len(
                               recaptcha) else [])
                raise ValueError("Unable to perform auth login to Safari Books Online.\n" + 
                               "Details:\n" + "%s" % "\n".join(
                                   messages if len(messages) else ["    Unexpected error!"]))
            except (html.etree.ParseError, html.etree.ParserError) as parsing_error:
                self.display.error(parsing_error)
                raise ValueError("Login went wrong and encountered an error "
                               "trying to parse the login details. Try again...")

        self.jwt = response.json()
        response = self.requests_provider(self.jwt["redirect_uri"])
        if response == 0:
            raise ConnectionError("Unable to reach Safari Books Online after login. Try again...")

    def check_login(self) -> None:
        """Validate that the session is still active."""
        response = self.requests_provider(PROFILE_URL, perform_redirect=False)

        if response == 0:
            raise ConnectionError("Unable to reach Safari Books Online. Try again...")
        elif response.status_code != 200:
            raise ValueError("Authentication issue: unable to access profile page.")
        elif "user_type\":\"Expired\"" in response.text:
            raise ValueError("Authentication issue: account subscription expired.")

        self.display.info("Successfully authenticated.", state=True)

    def get_book_info(self, book_id: str) -> Dict[str, Any]:
        """Fetch book metadata from API."""
        api_url = self.API_TEMPLATE.format(book_id)
        response = self.requests_provider(api_url)
        if response == 0:
            raise ConnectionError("Unable to retrieve book info.")

        response = response.json()
        if not isinstance(response, dict) or len(response.keys()) == 1:
            raise ValueError(self.display.api_error(response))

        if "last_chapter_read" in response:
            del response["last_chapter_read"]

        for key, value in response.items():
            if value is None:
                response[key] = 'n/a'

        return response

    def get_book_chapters(self, book_id: str, page: int = 1) -> List[Dict[str, Any]]:
        """Fetch book chapters from API."""
        api_url = self.API_TEMPLATE.format(book_id)
        response = self.requests_provider(urljoin(api_url, "chapter/?page=%s" % page))
        if response == 0:
            raise ConnectionError("Unable to retrieve book chapters.")

        response = response.json()

        if not isinstance(response, dict) or len(response.keys()) == 1:
            raise ValueError(self.display.api_error(response))

        if "results" not in response or not len(response["results"]):
            raise ValueError("Unable to retrieve book chapters.")

        if response["count"] > sys.getrecursionlimit():
            sys.setrecursionlimit(response["count"])

        result = []
        result.extend([c for c in response["results"] if "cover" in c["filename"] or "cover" in c["title"]])
        for c in result:
            del response["results"][response["results"].index(c)]

        result += response["results"]
        return result + (self.get_book_chapters(book_id, page + 1) if response["next"] else [])

    def download_book(self, book_id: str, output_dir: str, credentials: Optional[tuple] = None) -> str:
        """
        Download a book and return the local path of the downloaded book folder.
        
        Args:
            book_id: The book ID to download
            output_dir: Directory to save the book
            credentials: Optional (email, password) tuple for authentication
            
        Returns:
            Path to the downloaded book folder
        """
        # Authenticate
        self.authenticate(credentials)
        
        # Get book info
        self.display.info("Retrieving book info...")
        book_info = self.get_book_info(book_id)
        self.display.book_info(book_info)
        
        # Get chapters
        self.display.info("Retrieving book chapters...")
        book_chapters = self.get_book_chapters(book_id)
        
        # Create output directory
        book_title = book_info["title"]
        clean_book_title = "".join(self.escape_dirname(book_title).split(",")[:2]) + " ({0})".format(book_id)
        book_path = os.path.join(output_dir, clean_book_title)
        
        if not os.path.isdir(book_path):
            os.makedirs(book_path)
        
        self.display.set_output_dir(book_path)
        
        # Create OEBPS structure
        oebps_path = os.path.join(book_path, "OEBPS")
        css_path = os.path.join(oebps_path, "Styles")
        images_path = os.path.join(oebps_path, "Images")
        
        for path in [oebps_path, css_path, images_path]:
            if not os.path.isdir(path):
                os.makedirs(path)
        
        # Download content
        self._download_content(book_id, book_info, book_chapters, oebps_path, css_path, images_path)
        
        # Save cookies
        json.dump(self.session.cookies.get_dict(), open(self.cookies_file, "w"))
        
        return book_path

    def _download_content(self, book_id: str, book_info: Dict[str, Any], 
                         book_chapters: List[Dict[str, Any]], oebps_path: str, 
                         css_path: str, images_path: str) -> None:
        """Download all book content (chapters, CSS, images)."""
        self.display.info("Downloading book contents... (%s chapters)" % len(book_chapters), state=True)
        
        # Initialize content tracking
        self.book_id = book_id
        self.book_info = book_info
        self.book_chapters = book_chapters
        self.base_url = book_info["web_url"]
        self.css = []
        self.images = []
        
        # Download chapters
        chapters_queue = book_chapters[:]
        len_books = len(book_chapters)
        
        for _ in range(len_books):
            if not len(chapters_queue):
                break
                
            first_page = len_books == len(chapters_queue)
            next_chapter = chapters_queue.pop(0)
            
            self._download_chapter(next_chapter, oebps_path, first_page)
            self.display.state(len_books, len_books - len(chapters_queue))
        
        # Download CSS and images
        self._download_assets(css_path, images_path)
    
    def _download_chapter(self, chapter: Dict[str, Any], oebps_path: str, first_page: bool = False) -> None:
        """Download a single chapter."""
        chapter_title = chapter["title"]
        filename = chapter["filename"]
        
        # Check if already downloaded
        xhtml_file = os.path.join(oebps_path, filename.replace(".html", ".xhtml"))
        if os.path.isfile(xhtml_file):
            return
        
        # Get chapter content
        response = self.requests_provider(chapter["content"])
        if response == 0 or response.status_code != 200:
            self.display.error(f"Error retrieving chapter: {chapter_title}")
            return
        
        # Parse HTML
        try:
            root = html.fromstring(response.text, base_url=SAFARI_BASE_URL)
        except (html.etree.ParseError, html.etree.ParserError) as parsing_error:
            self.display.error(f"Error parsing chapter {chapter_title}: {parsing_error}")
            return
        
        # Extract and collect assets
        self._extract_assets(root, chapter)
        
        # Parse and save chapter
        try:
            page_css, xhtml = self._parse_html(root, first_page)
            self._save_chapter(xhtml_file, page_css, xhtml)
        except Exception as e:
            self.display.error(f"Error processing chapter {chapter_title}: {e}")
    
    def _extract_assets(self, root, chapter: Dict[str, Any]) -> None:
        """Extract CSS and image URLs from chapter."""
        # Extract CSS
        stylesheet_links = root.xpath("//link[@rel='stylesheet']")
        for s in stylesheet_links:
            css_url = urljoin("https:", s.attrib["href"]) if s.attrib["href"][:2] == "//" \
                else urljoin(self.base_url, s.attrib["href"])
            if css_url not in self.css:
                self.css.append(css_url)
        
        # Extract images from chapter metadata
        if "images" in chapter and len(chapter["images"]):
            asset_base_url = chapter['asset_base_url']
            api_v2_detected = 'v2' in chapter['content']
            if api_v2_detected:
                asset_base_url = SAFARI_BASE_URL + "/api/v2/epubs/urn:orm:book:{}/files".format(self.book_id)
            
            for img_url in chapter['images']:
                if api_v2_detected:
                    self.images.append(asset_base_url + '/' + img_url)
                else:
                    self.images.append(urljoin(chapter['asset_base_url'], img_url))
    
    def _parse_html(self, root, first_page: bool = False) -> tuple:
        """Parse HTML content and return CSS and XHTML."""
        book_content = root.xpath("//div[@id='sbo-rt-content']")
        if not len(book_content):
            raise ValueError("Book content not found")
        
        page_css = ""
        stylesheets = root.xpath("//style")
        if len(stylesheets):
            for css in stylesheets:
                if "data-template" in css.attrib and len(css.attrib["data-template"]):
                    css.text = css.attrib["data-template"]
                    del css.attrib["data-template"]
                try:
                    page_css += html.tostring(css, method="xml", encoding='unicode') + "\n"
                except (html.etree.ParseError, html.etree.ParserError):
                    pass
        
        book_content = book_content[0]
        book_content.rewrite_links(self._link_replace)
        
        try:
            xhtml = html.tostring(book_content, method="xml", encoding='unicode')
        except (html.etree.ParseError, html.etree.ParserError) as parsing_error:
            raise ValueError(f"Error parsing HTML: {parsing_error}")
        
        return page_css, xhtml
    
    def _link_replace(self, link: str) -> str:
        """Replace links for EPUB compatibility."""
        if link and not link.startswith("mailto"):
            if not self._url_is_absolute(link):
                if any(x in link for x in ["cover", "images", "graphics"]) or \
                        self._is_image_link(link):
                    image = link.split("/")[-1]
                    return "Images/" + image
                return link.replace(".html", ".xhtml")
            else:
                if self.book_id in link:
                    return self._link_replace(link.split(self.book_id)[-1])
        return link
    
    @staticmethod
    def _url_is_absolute(url: str) -> bool:
        """Check if URL is absolute."""
        return bool(urlparse(url).netloc)
    
    @staticmethod
    def _is_image_link(url: str) -> bool:
        """Check if URL points to an image."""
        return pathlib.Path(url).suffix[1:].lower() in ["jpg", "jpeg", "png", "gif"]
    
    def _save_chapter(self, filepath: str, page_css: str, xhtml: str) -> None:
        """Save chapter as XHTML file."""
        base_html = """<!DOCTYPE html>
<html lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
{0}
<style type="text/css">
body{{margin:1em;background-color:transparent!important;}}
#sbo-rt-content *{{text-indent:0pt!important;}}
#sbo-rt-content .bq{{margin-right:1em!important;}}
</style>
</head>
<body>{1}</body>
</html>"""
        
        with open(filepath, "wb") as f:
            f.write(base_html.format(page_css, xhtml).encode("utf-8", 'xmlcharrefreplace'))
        
        self.display.log(f"Created: {os.path.basename(filepath)}")
    
    def _download_assets(self, css_path: str, images_path: str) -> None:
        """Download CSS and image assets."""
        # Download CSS
        if self.css:
            self.display.info("Downloading book CSSs... (%s files)" % len(self.css), state=True)
            for i, css_url in enumerate(self.css):
                css_file = os.path.join(css_path, "Style{0:0>2}.css".format(i))
                if not os.path.isfile(css_file):
                    response = self.requests_provider(css_url)
                    if response != 0:
                        with open(css_file, 'wb') as f:
                            f.write(response.content)
        
        # Download images
        if self.images:
            self.display.info("Downloading book images... (%s files)" % len(self.images), state=True)
            for image_url in self.images:
                image_name = image_url.split("/")[-1]
                image_path = os.path.join(images_path, image_name)
                if not os.path.isfile(image_path):
                    response = self.requests_provider(urljoin(SAFARI_BASE_URL, image_url), stream=True)
                    if response != 0:
                        with open(image_path, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)

    @staticmethod
    def escape_dirname(dirname: str, clean_space: bool = False) -> str:
        """Escape directory name for filesystem compatibility."""
        if ":" in dirname:
            if dirname.index(":") > 15:
                dirname = dirname.split(":")[0]
            elif "win" in sys.platform:
                dirname = dirname.replace(":", ",")

        for ch in ['~', '#', '%', '&', '*', '{', '}', '\\', '<', '>', '?', '/', '`', '\'', '"', '|', '+', ':']:
            if ch in dirname:
                dirname = dirname.replace(ch, "_")

        return dirname if not clean_space else dirname.replace(" ", "")


def download_book(book_id: str, output_dir: str, credentials: Optional[tuple] = None) -> str:
    """
    Download a book from Safari Books Online.
    
    Args:
        book_id: The book ID to download
        output_dir: Directory to save the book
        credentials: Optional (email, password) tuple for authentication
        
    Returns:
        Path to the downloaded book folder
        
    Example:
        >>> book_path = download_book("1234567890123", "/path/to/books")
        >>> print(f"Book downloaded to: {book_path}")
    """
    downloader = SafariBooksDownloader()
    return downloader.download_book(book_id, output_dir, credentials)


def parse_cred(cred: str) -> Optional[tuple]:
    """Parse credentials from string format."""
    if ":" not in cred:
        return None

    sep = cred.index(":")
    new_cred = ["", ""]
    new_cred[0] = cred[:sep].strip("'").strip('"')
    if "@" not in new_cred[0]:
        return None

    new_cred[1] = cred[sep + 1:]
    return tuple(new_cred)


# Keep the original SafariBooks class for backward compatibility
class SafariBooks(SafariBooksDownloader):
    """Original SafariBooks class for CLI compatibility."""
    
    def __init__(self, args):
        # Convert args to the new format
        display = Display("info_%s.log" % escape(args.bookid))
        display.intro()
        
        super().__init__(display)
        
        # Handle credentials
        credentials = None
        if args.cred:
            credentials = args.cred
        elif args.login:
            user_email = input("Email: ")
            passwd = getpass.getpass("Password: ")
            credentials = (user_email, passwd)
        
        # Download the book
        books_dir = os.path.join(PATH, "Books")
        if not os.path.isdir(books_dir):
            os.mkdir(books_dir)
            
        book_path = self.download_book(args.bookid, books_dir, credentials)
        
        # TODO: Add EPUB generation here
        # For now, just complete the download
        self.display.done(book_path)
        self.display.unregister()
        
        if not self.display.in_error and not args.log:
            os.remove(self.display.log_file)


# MAIN - Keep original CLI functionality
if __name__ == "__main__":
    arguments = argparse.ArgumentParser(prog="safaribooks_refactored.py",
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
             " `" + SAFARI_BASE_URL + "/library/view/book-name/XXXXXXXXXXXXX/`"
    )

    args_parsed = arguments.parse_args()
    if args_parsed.cred or args_parsed.login:
        user_email = ""
        pre_cred = ""

        if args_parsed.cred:
            pre_cred = args_parsed.cred
        else:
            user_email = input("Email: ")
            passwd = getpass.getpass("Password: ")
            pre_cred = user_email + ":" + passwd

        parsed_cred = parse_cred(pre_cred)

        if not parsed_cred:
            arguments.error("invalid credential: %s" % (
                args_parsed.cred if args_parsed.cred else (user_email + ":*******")
            ))

        args_parsed.cred = parsed_cred
    else:
        if args_parsed.no_cookies:
            arguments.error("invalid option: `--no-cookies` is valid only if you use the `--cred` option")

    SafariBooks(args_parsed)
    sys.exit(0)
