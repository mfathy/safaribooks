#!/usr/bin/env python3
# coding: utf-8
"""
Download Module for SafariBooks
Handles book info retrieval, chapter downloading, and content processing
"""

import os
import sys
import pathlib
import random
from urllib.parse import urljoin, urlparse
from lxml import html, etree
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SAFARI_BASE_URL, API_TEMPLATE


class BookDownloader:
    """Handles downloading and processing of book content"""
    
    def __init__(self, session, display, book_id, cookie_update_callback=None):
        self.session = session
        self.display = display
        self.book_id = book_id
        self.api_url = API_TEMPLATE.format(book_id)
        self.cookie_update_callback = cookie_update_callback
        
        # Book data
        self.book_info = {}
        self.book_chapters = []
        self.book_title = ""
        self.base_url = ""
        
        # Content collections
        self.css = []
        self.images = []
        self.chapter_stylesheets = []
        
        # File paths
        self.BOOK_PATH = ""
        self.css_path = ""
        self.images_path = ""
        
        # Current processing state
        self.chapter_title = ""
        self.filename = ""
        self.cover = False
    
    def get_book_info(self):
        """Retrieve book information from API"""
        response = self._make_request(self.api_url)
        if response == 0:
            self.display.exit("API: unable to retrieve book info.")
        
        response = response.json()
        if not isinstance(response, dict) or len(response.keys()) == 1:
            self.display.exit(self.display.api_error(response))
        
        if "last_chapter_read" in response:
            del response["last_chapter_read"]
        
        for key, value in response.items():
            if value is None:
                response[key] = 'n/a'
        
        self.book_info = response
        return response
    
    def get_book_chapters(self, page=1):
        """Retrieve book chapters from API"""
        response = self._make_request(urljoin(self.api_url, f"chapter/?page={page}"))
        if response == 0:
            self.display.exit("API: unable to retrieve book chapters.")
        
        response = response.json()
        if not isinstance(response, dict) or len(response.keys()) == 1:
            self.display.exit(self.display.api_error(response))
        
        if "results" not in response or not len(response["results"]):
            self.display.exit("API: unable to retrieve book chapters.")
        
        if response["count"] > sys.getrecursionlimit():
            sys.setrecursionlimit(response["count"])
        
        result = []
        result.extend([c for c in response["results"] if "cover" in c["filename"] or "cover" in c["title"]])
        for c in result:
            del response["results"][response["results"].index(c)]
        
        result += response["results"]
        chapters = result + (self.get_book_chapters(page + 1) if response["next"] else [])
        
        self.book_chapters = chapters
        return chapters
    
    def get_html(self, url):
        """Retrieve and parse HTML content from URL"""
        response = self._make_request(url)
        if response == 0 or response.status_code != 200:
            self.display.exit(
                "Crawler: error trying to retrieve this page: %s (%s)\n    From: %s" %
                (self.filename, self.chapter_title, url),
                raise_exception=True
            )
        
        root = None
        try:
            root = html.fromstring(response.text, base_url=SAFARI_BASE_URL)
        except (html.etree.ParseError, html.etree.ParserError) as parsing_error:
            self.display.error(parsing_error)
            self.display.exit(
                "Crawler: error trying to parse this page: %s (%s)\n    From: %s" %
                (self.filename, self.chapter_title, url)
            )
        return root
    
    def get_default_cover(self):
        """Download default cover image, trying high-res first"""
        cover_url = self.book_info.get("cover", "")
        
        if not cover_url:
            return False
        
        # Try to get high-resolution version by modifying URL
        # O'Reilly covers often have size parameters or specific patterns
        high_res_urls = [
            cover_url.replace("w=200", "w=800"),  # Increase width
            cover_url.replace("w=250", "w=800"),
            cover_url.replace("w=300", "w=800"),
            cover_url.replace("/small/", "/large/"),
            cover_url.replace("/thumb/", "/large/"),
            cover_url.replace("/medium/", "/large/"),
            cover_url + "?width=800",  # Add width parameter
            cover_url  # Original as fallback
        ]
        
        # Try each URL until one works
        for url in high_res_urls:
            response = self._make_request(url, stream=True)
            if response != 0:
                try:
                    file_ext = response.headers.get("Content-Type", "image/jpeg").split("/")[-1]
                    if file_ext not in ["jpeg", "jpg", "png", "gif", "webp"]:
                        file_ext = "jpeg"
                    
                    cover_path = os.path.join(self.images_path, f"default_cover.{file_ext}")
                    with open(cover_path, 'wb') as i:
                        for chunk in response.iter_content(1024):
                            i.write(chunk)
                    
                    # Check if we got a reasonable file size (at least 10KB)
                    if os.path.getsize(cover_path) > 10000:
                        self.display.info(f"Downloaded high-res cover: {os.path.getsize(cover_path) // 1024}KB")
                        return f"default_cover.{file_ext}"
                except Exception as e:
                    self.display.debug(f"Failed to download from {url}: {e}")
                    continue
        
        self.display.error("Error trying to retrieve the cover: %s" % cover_url)
        return False
    
    @staticmethod
    def url_is_absolute(url):
        """Check if URL is absolute"""
        return bool(urlparse(url).netloc)
    
    @staticmethod
    def is_image_link(url: str):
        """Check if URL points to an image"""
        return pathlib.Path(url).suffix[1:].lower() in ["jpg", "jpeg", "png", "gif"]
    
    def link_replace(self, link):
        """Process and replace links in content"""
        if link and not link.startswith("mailto"):
            if not self.url_is_absolute(link):
                if any(x in link for x in ["cover", "images", "graphics"]) or self.is_image_link(link):
                    image = link.split("/")[-1]
                    return "Images/" + image
                return link.replace(".html", ".xhtml")
            else:
                if self.book_id in link:
                    return self.link_replace(link.split(self.book_id)[-1])
        return link
    
    @staticmethod
    def get_cover(html_root):
        """Extract cover image from HTML"""
        lowercase_ns = etree.FunctionNamespace(None)
        lowercase_ns["lower-case"] = lambda _, n: n[0].lower() if n and len(n) else ""
        
        images = html_root.xpath("//img[contains(lower-case(@id), 'cover') or contains(lower-case(@class), 'cover') or"
                                 "contains(lower-case(@name), 'cover') or contains(lower-case(@src), 'cover') or"
                                 "contains(lower-case(@alt), 'cover')]")
        if len(images):
            return images[0]
        
        divs = html_root.xpath("//div[contains(lower-case(@id), 'cover') or contains(lower-case(@class), 'cover') or"
                               "contains(lower-case(@name), 'cover') or contains(lower-case(@src), 'cover')]//img")
        if len(divs):
            return divs[0]
        
        a = html_root.xpath("//a[contains(lower-case(@id), 'cover') or contains(lower-case(@class), 'cover') or"
                            "contains(lower-case(@name), 'cover') or contains(lower-case(@src), 'cover')]//img")
        if len(a):
            return a[0]
        return None
    
    def parse_html(self, root, first_page=False):
        """Parse HTML content and extract CSS/images"""
        if random.random() > 0.8:
            if len(root.xpath("//div[@class='controls']/a/text()")):
                self.display.exit(self.display.api_error(" "))
        
        book_content = root.xpath("//div[@id='sbo-rt-content']")
        if not len(book_content):
            self.display.exit(
                "Parser: book content's corrupted or not present: %s (%s)" %
                (self.filename, self.chapter_title)
            )
        
        page_css = ""
        if len(self.chapter_stylesheets):
            for chapter_css_url in self.chapter_stylesheets:
                if chapter_css_url not in self.css:
                    self.css.append(chapter_css_url)
                    self.display.log("Crawler: found a new CSS at %s" % chapter_css_url)
                page_css += "<link href=\"Styles/Style{0:0>2}.css\" " \
                            "rel=\"stylesheet\" type=\"text/css\" />\n".format(self.css.index(chapter_css_url))
        
        stylesheet_links = root.xpath("//link[@rel='stylesheet']")
        if len(stylesheet_links):
            for s in stylesheet_links:
                css_url = urljoin("https:", s.attrib["href"]) if s.attrib["href"][:2] == "//" \
                    else urljoin(self.base_url, s.attrib["href"])
                if css_url not in self.css:
                    self.css.append(css_url)
                    self.display.log("Crawler: found a new CSS at %s" % css_url)
                page_css += "<link href=\"Styles/Style{0:0>2}.css\" " \
                            "rel=\"stylesheet\" type=\"text/css\" />\n".format(self.css.index(css_url))
        
        stylesheets = root.xpath("//style")
        if len(stylesheets):
            for css in stylesheets:
                if "data-template" in css.attrib and len(css.attrib["data-template"]):
                    css.text = css.attrib["data-template"]
                    del css.attrib["data-template"]
                try:
                    page_css += html.tostring(css, method="xml", encoding='unicode') + "\n"
                except (html.etree.ParseError, html.etree.ParserError) as parsing_error:
                    self.display.error(parsing_error)
                    self.display.exit(
                        "Parser: error trying to parse one CSS found in this page: %s (%s)" %
                        (self.filename, self.chapter_title)
                    )
        
        # Handle SVG images
        svg_image_tags = root.xpath("//image")
        if len(svg_image_tags):
            for img in svg_image_tags:
                image_attr_href = [x for x in img.attrib.keys() if "href" in x]
                if len(image_attr_href):
                    svg_url = img.attrib.get(image_attr_href[0])
                    svg_root = img.getparent().getparent()
                    new_img = svg_root.makeelement("img")
                    new_img.attrib.update({"src": svg_url})
                    svg_root.remove(img.getparent())
                    svg_root.append(new_img)
        
        book_content = book_content[0]
        book_content.rewrite_links(self.link_replace)
        
        xhtml = None
        try:
            if first_page:
                is_cover = self.get_cover(book_content)
                if is_cover is not None:
                    page_css = "<style>" \
                               "body{display:table;position:absolute;margin:0!important;height:100%;width:100%;}" \
                               "#Cover{display:table-cell;vertical-align:middle;text-align:center;}" \
                               "img{height:90vh;margin-left:auto;margin-right:auto;}" \
                               "</style>"
                    cover_html = html.fromstring("<div id=\"Cover\"></div>")
                    cover_div = cover_html.xpath("//div")[0]
                    cover_img = cover_div.makeelement("img")
                    cover_img.attrib.update({"src": is_cover.attrib["src"]})
                    cover_div.append(cover_img)
                    book_content = cover_html
                    self.cover = is_cover.attrib["src"]
            
            xhtml = html.tostring(book_content, method="xml", encoding='unicode')
        except (html.etree.ParseError, html.etree.ParserError) as parsing_error:
            self.display.error(parsing_error)
            self.display.exit(
                "Parser: error trying to parse HTML of this page: %s (%s)" %
                (self.filename, self.chapter_title)
            )
        return page_css, xhtml
    
    def _make_request(self, url, **kwargs):
        """Make HTTP request using the session and update cookies"""
        try:
            if 'stream' in kwargs and kwargs['stream']:
                response = self.session.get(url, stream=True, **{k: v for k, v in kwargs.items() if k != 'stream'})
            else:
                response = self.session.get(url, **{k: v for k, v in kwargs.items() if k != 'stream'})
            
            # Update cookies from response (CRITICAL FIX: keeps authentication fresh)
            if self.cookie_update_callback and hasattr(response, 'raw') and hasattr(response.raw, 'headers'):
                set_cookie_headers = response.raw.headers.getlist("Set-Cookie")
                if set_cookie_headers:
                    self.cookie_update_callback(set_cookie_headers)
            
            return response
        except Exception as e:
            self.display.error(f"Request error: {e}")
            return 0
    
    def download_chapters(self, chapters_queue, base_html_template):
        """Download all book chapters"""
        len_books = len(self.book_chapters)
        
        for _ in range(len_books):
            if not len(chapters_queue):
                return
            
            first_page = len_books == len(chapters_queue)
            next_chapter = chapters_queue.pop(0)
            self.chapter_title = next_chapter["title"]
            self.filename = next_chapter["filename"]
            
            asset_base_url = next_chapter['asset_base_url']
            api_v2_detected = False
            if 'v2' in next_chapter['content']:
                asset_base_url = SAFARI_BASE_URL + "/api/v2/epubs/urn:orm:book:{}/files".format(self.book_id)
                api_v2_detected = True
            
            if "images" in next_chapter and len(next_chapter["images"]):
                for img_url in next_chapter['images']:
                    if api_v2_detected:
                        self.images.append(asset_base_url + '/' + img_url)
                    else:
                        self.images.append(urljoin(next_chapter['asset_base_url'], img_url))
            
            # Stylesheets
            self.chapter_stylesheets = []
            if "stylesheets" in next_chapter and len(next_chapter["stylesheets"]):
                self.chapter_stylesheets.extend(x["url"] for x in next_chapter["stylesheets"])
            
            if "site_styles" in next_chapter and len(next_chapter["site_styles"]):
                self.chapter_stylesheets.extend(next_chapter["site_styles"])
            
            if os.path.isfile(os.path.join(self.BOOK_PATH, "OEBPS", self.filename.replace(".html", ".xhtml"))):
                if not self.display.book_ad_info and \
                        next_chapter not in self.book_chapters[:self.book_chapters.index(next_chapter)]:
                    self.display.info(
                        ("File `%s` already exists.\n"
                         "    If you want to download again all the book,\n"
                         "    please delete the output directory '" + self.BOOK_PATH + "' and restart the program.")
                         % self.filename.replace(".html", ".xhtml")
                    )
                    self.display.book_ad_info = 2
            else:
                self.save_page_html(self.parse_html(self.get_html(next_chapter["content"]), first_page), base_html_template)
            
            self.display.state(len_books, len_books - len(chapters_queue))
    
    def save_page_html(self, contents, base_html_template):
        """Save processed HTML content to file"""
        self.filename = self.filename.replace(".html", ".xhtml")
        with open(os.path.join(self.BOOK_PATH, "OEBPS", self.filename), "wb") as f:
            f.write(base_html_template.format(contents[0], contents[1]).encode("utf-8", 'xmlcharrefreplace'))
        self.display.log("Created: %s" % self.filename)
