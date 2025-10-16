#!/usr/bin/env python3
# coding: utf-8
"""
Legacy EPUB Generation Module for SafariBooks
Handles EPUB 2.0 file creation, packaging, and metadata generation
"""

import os
import shutil
import sys
from html import escape
from multiprocessing import Queue
from urllib.parse import urljoin
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SAFARI_BASE_URL, CONTAINER_XML, CONTENT_OPF, TOC_NCX


class WinQueue(list):
    """Windows-compatible queue implementation"""
    def put(self, el):
        self.append(el)
    
    def qsize(self):
        return self.__len__()


class LegacyEpubGenerator:
    """Handles legacy EPUB 2.0 file generation and packaging"""
    
    def __init__(self, session, display, book_info, book_chapters, book_path, css_path, images_path):
        self.session = session
        self.display = display
        self.book_info = book_info
        self.book_chapters = book_chapters
        self.book_path = book_path
        self.css_path = css_path
        self.images_path = images_path
        
        # Content collections
        self.css = []
        self.images = []
        self.cover = False
        
        # Queues for multiprocessing
        self.css_done_queue = None
        self.images_done_queue = None
    
    def create_content_opf(self):
        """Create content.opf file for EPUB"""
        self.css = next(os.walk(self.css_path))[2]
        self.images = next(os.walk(self.images_path))[2]
        
        manifest = []
        spine = []
        for c in self.book_chapters:
            c["filename"] = c["filename"].replace(".html", ".xhtml")
            item_id = escape("".join(c["filename"].split(".")[:-1]))
            manifest.append("<item id=\"{0}\" href=\"{1}\" media-type=\"application/xhtml+xml\" />".format(
                item_id, c["filename"]
            ))
            spine.append("<itemref idref=\"{0}\"/>".format(item_id))
        
        for i in set(self.images):
            dot_split = i.split(".")
            head = "img_" + escape("".join(dot_split[:-1]))
            extension = dot_split[-1]
            manifest.append("<item id=\"{0}\" href=\"Images/{1}\" media-type=\"image/{2}\" />".format(
                head, i, "jpeg" if "jp" in extension else extension
            ))
        
        for i in range(len(self.css)):
            manifest.append("<item id=\"style_{0:0>2}\" href=\"Styles/Style{0:0>2}.css\" "
                            "media-type=\"text/css\" />".format(i))
        
        authors = "\n".join("<dc:creator opf:file-as=\"{0}\" opf:role=\"aut\">{0}</dc:creator>".format(
            escape(aut.get("name", "n/d"))
        ) for aut in self.book_info.get("authors", []))
        
        subjects = "\n".join("<dc:subject>{0}</dc:subject>".format(escape(sub.get("name", "n/d")))
                             for sub in self.book_info.get("subjects", []))
        
        return CONTENT_OPF.format(
            (self.book_info.get("isbn", self.book_info.get("identifier", ""))),
            escape(self.book_info.get("title", "")),
            authors,
            escape(self.book_info.get("description", "")),
            subjects,
            ", ".join(escape(pub.get("name", "")) for pub in self.book_info.get("publishers", [])),
            escape(self.book_info.get("rights", "")),
            self.book_info.get("issued", ""),
            self.cover,
            "\n".join(manifest),
            "\n".join(spine),
            self.book_chapters[0]["filename"].replace(".html", ".xhtml")
        )
    
    @staticmethod
    def parse_toc(l, c=0, mx=0):
        """Parse table of contents structure with proper chapter anchors"""
        r = ""
        for cc in l:
            c += 1
            if int(cc["depth"]) > mx:
                mx = int(cc["depth"])
            
            # Build href with fragment identifier for chapter start
            href = cc["href"].replace(".html", ".xhtml").split("/")[-1]
            
            # If there's a fragment (anchor), include it in the href
            if cc.get("fragment") and len(cc["fragment"]) > 0:
                href = f"{href}#{cc['fragment']}"
            
            r += "<navPoint id=\"{0}\" playOrder=\"{1}\">" \
                 "<navLabel><text>{2}</text></navLabel>" \
                 "<content src=\"{3}\"/>".format(
                    cc["fragment"] if len(cc["fragment"]) else cc["id"], c,
                    escape(cc["label"]), href
                 )
            
            if cc["children"]:
                sr, c, mx = LegacyEpubGenerator.parse_toc(cc["children"], c, mx)
                r += sr
            
            r += "</navPoint>\n"
        
        return r, c, mx
    
    def create_toc(self, api_url):
        """Create table of contents NCX file"""
        response = self._make_request(urljoin(api_url, "toc/"))
        if response == 0:
            self.display.exit("API: unable to retrieve book chapters. "
                              "Don't delete any files, just run again this program"
                              " in order to complete the `.epub` creation!")
        
        response = response.json()
        if not isinstance(response, list) and len(response.keys()) == 1:
            self.display.exit(
                self.display.api_error(response) +
                " Don't delete any files, just run again this program"
                " in order to complete the `.epub` creation!"
            )
        
        navmap, _, max_depth = self.parse_toc(response)
        return TOC_NCX.format(
            (self.book_info["isbn"] if self.book_info["isbn"] else self.book_info.get("identifier", "")),
            max_depth,
            self.book_info.get("title", ""),
            ", ".join(aut.get("name", "") for aut in self.book_info.get("authors", [])),
            navmap
        )
    
    def _thread_download_css(self, url):
        """Download CSS file in thread"""
        css_file = os.path.join(self.css_path, "Style{0:0>2}.css".format(self.css.index(url)))
        if os.path.isfile(css_file):
            if not self.display.css_ad_info.value and url not in self.css[:self.css.index(url)]:
                self.display.info(("File `%s` already exists.\n"
                                   "    If you want to download again all the CSSs,\n"
                                   "    please delete the output directory '" + self.book_path + "'"
                                   " and restart the program.") %
                                  css_file)
                self.display.css_ad_info.value = 1
        else:
            response = self._make_request(url)
            if response == 0:
                self.display.error("Error trying to retrieve this CSS: %s\n    From: %s" % (css_file, url))
            
            with open(css_file, 'wb') as s:
                s.write(response.content)
        
        self.css_done_queue.put(1)
        self.display.state(len(self.css), self.css_done_queue.qsize())
    
    def _thread_download_images(self, url):
        """Download image file in thread"""
        image_name = url.split("/")[-1]
        image_path = os.path.join(self.images_path, image_name)
        if os.path.isfile(image_path):
            if not self.display.images_ad_info.value and url not in self.images[:self.images.index(url)]:
                self.display.info(("File `%s` already exists.\n"
                                   "    If you want to download again all the images,\n"
                                   "    please delete the output directory '" + self.book_path + "'"
                                   " and restart the program.") %
                                  image_name)
                self.display.images_ad_info.value = 1
        else:
            response = self._make_request(urljoin(SAFARI_BASE_URL, url), stream=True)
            if response == 0:
                self.display.error("Error trying to retrieve this image: %s\n    From: %s" % (image_name, url))
                return
            
            with open(image_path, 'wb') as img:
                for chunk in response.iter_content(1024):
                    img.write(chunk)
        
        self.images_done_queue.put(1)
        self.display.state(len(self.images), self.images_done_queue.qsize())
    
    def collect_css(self, css_list):
        """Download all CSS files"""
        self.css = css_list
        self.display.state_status.value = -1
        
        # Initialize queue
        self.css_done_queue = Queue(0) if "win" not in sys.platform else WinQueue()
        
        # Single-threaded download for stability
        for css_url in self.css:
            self._thread_download_css(css_url)
    
    def collect_images(self, images_list):
        """Download all image files"""
        self.images = images_list
        if self.display.book_ad_info == 2:
            self.display.info("Some of the book contents were already downloaded.\n"
                              "    If you want to be sure that all the images will be downloaded,\n"
                              "    please delete the output directory '" + self.book_path +
                              "' and restart the program.")
        
        self.display.state_status.value = -1
        
        # Initialize queue
        self.images_done_queue = Queue(0) if "win" not in sys.platform else WinQueue()
        
        # Single-threaded download for stability
        for image_url in self.images:
            self._thread_download_images(image_url)
    
    def create_epub(self, api_url, book_id, path):
        """Create the final EPUB file"""
        # Create mimetype file
        with open(os.path.join(self.book_path, "mimetype"), "w") as f:
            f.write("application/epub+zip")
        
        # Create META-INF directory
        meta_info = os.path.join(self.book_path, "META-INF")
        if os.path.isdir(meta_info):
            self.display.log("META-INF directory already exists: %s" % meta_info)
        else:
            os.makedirs(meta_info)
        
        # Create container.xml
        with open(os.path.join(meta_info, "container.xml"), "wb") as f:
            f.write(CONTAINER_XML.encode("utf-8", "xmlcharrefreplace"))
        
        # Create content.opf
        with open(os.path.join(self.book_path, "OEBPS", "content.opf"), "wb") as f:
            f.write(self.create_content_opf().encode("utf-8", "xmlcharrefreplace"))
        
        # Create toc.ncx
        with open(os.path.join(self.book_path, "OEBPS", "toc.ncx"), "wb") as f:
            f.write(self.create_toc(api_url).encode("utf-8", "xmlcharrefreplace"))
        
        # Create ZIP archive
        zip_file = os.path.join(path, "Books", book_id)
        if os.path.isfile(zip_file + ".zip"):
            os.remove(zip_file + ".zip")
        
        shutil.make_archive(zip_file, 'zip', self.book_path)
        os.rename(zip_file + ".zip", os.path.join(self.book_path, book_id) + ".epub")
    
    def _make_request(self, url, **kwargs):
        """Make HTTP request using the session"""
        try:
            if 'stream' in kwargs and kwargs['stream']:
                return self.session.get(url, stream=True, **{k: v for k, v in kwargs.items() if k != 'stream'})
            else:
                return self.session.get(url, **{k: v for k, v in kwargs.items() if k != 'stream'})
        except Exception as e:
            self.display.error(f"Request error: {e}")
            return 0
