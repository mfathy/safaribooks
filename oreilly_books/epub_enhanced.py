#!/usr/bin/env python3
# coding: utf-8
"""
Enhanced EPUB Generation Module for SafariBooks
Supports EPUB 3.3 with Kindle optimization and dual output formats
"""

import os
import shutil
import sys
import requests
from html import escape
from multiprocessing import Queue
from urllib.parse import urljoin
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SAFARI_BASE_URL, CONTAINER_XML, CONTENT_OPF, TOC_NCX


class WinQueue(list):
    """Windows-compatible queue implementation"""
    def put(self, el):
        self.append(el)
    
    def qsize(self):
        return self.__len__()


class EnhancedEpubGenerator:
    """Enhanced EPUB generator with EPUB 3.3 support and Kindle optimization"""
    
    # EPUB 3.3 Templates
    EPUB3_CONTAINER_XML = "<?xml version=\"1.0\"?>" \
                          "<container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">" \
                          "<rootfiles>" \
                          "<rootfile full-path=\"OEBPS/content.opf\" media-type=\"application/oebps-package+xml\" />" \
                          "</rootfiles>" \
                          "</container>"
    
    # Enhanced EPUB 3.3 content.opf with proper metadata
    EPUB3_CONTENT_OPF = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" \
                        "<package xmlns=\"http://www.idpf.org/2007/opf\" unique-identifier=\"bookid\" version=\"3.0\" >\n" \
                        "<metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\" " \
                        "xmlns:opf=\"http://www.idpf.org/2007/opf\">\n" \
                        "<dc:title>{1}</dc:title>\n" \
                        "{2}\n" \
                        "<dc:description>{3}</dc:description>\n" \
                        "{4}" \
                        "<dc:publisher>{5}</dc:publisher>\n" \
                        "<dc:rights>{6}</dc:rights>\n" \
                        "<dc:language>en-US</dc:language>\n" \
                        "<dc:date>{7}</dc:date>\n" \
                        "<dc:identifier id=\"bookid\">{0}</dc:identifier>\n" \
                        "<dc:format>application/epub+zip</dc:format>\n" \
                        "<meta name=\"cover\" content=\"{8}\"/>\n" \
                        "<meta property=\"dcterms:modified\">{9}</meta>\n" \
                        "<meta name=\"generator\" content=\"SafariBooks Enhanced EPUB Generator\"/>\n" \
                        "<meta property=\"schema:accessibilityFeature\" content=\"alternativeText\"/>\n" \
                        "<meta property=\"schema:accessibilityFeature\" content=\"structuralNavigation\"/>\n" \
                        "</metadata>\n" \
                        "<manifest>\n" \
                        "<item id=\"ncx\" href=\"toc.ncx\" media-type=\"application/x-dtbncx+xml\" />\n" \
                        "<item id=\"nav\" href=\"nav.xhtml\" media-type=\"application/xhtml+xml\" properties=\"nav\"/>\n" \
                        "{10}\n" \
                        "</manifest>\n" \
                        "<spine toc=\"ncx\">\n{11}</spine>\n" \
                        "<guide><reference href=\"{12}\" title=\"Cover\" type=\"cover\" /></guide>\n" \
                        "</package>"
    
    # Enhanced EPUB 3.3 navigation document
    EPUB3_NAV_XHTML = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" \
                      "<!DOCTYPE html>\n" \
                      "<html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\">\n" \
                      "<head>\n" \
                      "<title>Table of Contents</title>\n" \
                      "<style type=\"text/css\">\n" \
                      "body {{ font-family: Georgia, serif; margin: 1em; }}\n" \
                      "nav {{ margin: 1em 0; }}\n" \
                      "ol {{ list-style-type: none; padding-left: 0; }}\n" \
                      "li {{ margin: 0.5em 0; }}\n" \
                      "a {{ text-decoration: none; color: #0066cc; }}\n" \
                      "a:hover {{ text-decoration: underline; }}\n" \
                      "</style>\n" \
                      "</head>\n" \
                      "<body>\n" \
                      "<nav epub:type=\"toc\" id=\"toc\">\n" \
                      "<h1>Table of Contents</h1>\n" \
                      "<ol>\n{0}\n</ol>\n" \
                      "</nav>\n" \
                      "</body>\n" \
                      "</html>"
    
    # Enhanced EPUB 3.3 TOC NCX
    EPUB3_TOC_NCX = "<?xml version=\"1.0\" encoding=\"utf-8\" standalone=\"no\" ?>\n" \
                    "<!DOCTYPE ncx PUBLIC \"-//NISO//DTD ncx 2005-1//EN\"" \
                    " \"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd\">\n" \
                    "<ncx xmlns=\"http://www.daisy.org/z3986/2005/ncx/\" version=\"2005-1\">\n" \
                    "<head>\n" \
                    "<meta content=\"ID:ISBN:{0}\" name=\"dtb:uid\"/>\n" \
                    "<meta content=\"{1}\" name=\"dtb:depth\"/>\n" \
                    "<meta content=\"0\" name=\"dtb:totalPageCount\"/>\n" \
                    "<meta content=\"0\" name=\"dtb:maxPageNumber\"/>\n" \
                    "</head>\n" \
                    "<docTitle><text>{2}</text></docTitle>\n" \
                    "<docAuthor><text>{3}</text></docAuthor>\n" \
                    "<navMap>{4}</navMap>\n" \
                    "</ncx>"
    
    # Kindle-optimized CSS
    KINDLE_CSS = """
/* Kindle-optimized styles */
body {
    font-family: "Times New Roman", serif;
    font-size: 1.2em;
    line-height: 1.6;
    margin: 1em;
    color: #000;
    background: #fff;
}

/* Headers with proper alignment and page breaks */
h1, h2, h3, h4, h5, h6 {
    page-break-after: avoid;
    margin-top: 1.2em;
    margin-bottom: 0.6em;
    font-weight: bold;
    text-align: left;
    line-height: 1.3;
}

/* Chapter headers (h1) should have page break before */
h1 { 
    font-size: 1.8em;
    page-break-before: always;
    margin-top: 0;
    padding-top: 1em;
}

h2 { font-size: 1.5em; }
h3 { font-size: 1.3em; }
h4 { font-size: 1.1em; }
h5 { font-size: 1em; font-style: italic; }
h6 { font-size: 0.9em; font-style: italic; }

/* Primary text (paragraphs) with proper alignment */
p {
    margin: 0.6em 0;
    text-align: justify;
    text-indent: 0;
    orphans: 2;
    widows: 2;
    line-height: 1.6;
}

/* First paragraph after header - no indent */
h1 + p, h2 + p, h3 + p, h4 + p, h5 + p, h6 + p {
    text-indent: 0;
}

/* Secondary text (smaller, italics, etc.) */
.secondary, .subtitle, .author {
    text-align: center;
    font-style: italic;
    margin: 0.5em 0;
    color: #555;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
    page-break-inside: avoid;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    page-break-inside: avoid;
}

table, th, td {
    border: 1px solid #000;
}

th, td {
    padding: 0.5em;
    text-align: left;
    vertical-align: top;
}

th {
    font-weight: bold;
    background-color: #f0f0f0;
}

pre, code {
    font-family: "Courier New", monospace;
    font-size: 0.9em;
    white-space: pre-wrap;
    word-wrap: break-word;
    page-break-inside: avoid;
    background: #f5f5f5;
    padding: 0.3em 0.5em;
}

pre {
    margin: 1em 0;
    padding: 0.8em;
    border: 1px solid #ddd;
}

blockquote {
    margin: 1em 2em;
    padding-left: 1em;
    border-left: 3px solid #ccc;
    font-style: italic;
    page-break-inside: avoid;
}

/* Lists */
ul, ol {
    margin: 0.5em 0;
    padding-left: 2em;
}

li {
    margin: 0.3em 0;
}

/* Page breaks - improved */
.page-break, .pagebreak {
    page-break-before: always;
    margin: 0;
    padding: 0;
    height: 0;
}

.no-break {
    page-break-inside: avoid;
}

/* Avoid breaking after headers */
h1, h2, h3, h4, h5, h6 {
    break-after: avoid-page;
    page-break-after: avoid;
}

/* Cover page */
.cover-page {
    text-align: center;
    page-break-after: always;
}

.cover-page img {
    max-height: 90vh;
    max-width: 100%;
    width: auto;
    height: auto;
}

/* Section breaks */
.section-break {
    text-align: center;
    margin: 2em 0;
}

hr {
    border: 0;
    border-top: 1px solid #ccc;
    margin: 1.5em 0;
    page-break-after: avoid;
}
"""
    
    # Standard EPUB CSS
    STANDARD_CSS = """
/* Standard EPUB styles */
body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.1em;
    line-height: 1.5;
    margin: 1em;
    color: #333;
    background: #fff;
}

/* Headers with proper alignment and page breaks */
h1, h2, h3, h4, h5, h6 {
    margin-top: 1.5em;
    margin-bottom: 0.6em;
    font-weight: bold;
    color: #000;
    text-align: left;
    line-height: 1.3;
    page-break-after: avoid;
}

/* Chapter headers (h1) with page break */
h1 { 
    font-size: 2em;
    page-break-before: always;
    margin-top: 0;
    padding-top: 1em;
}

h2 { font-size: 1.6em; }
h3 { font-size: 1.3em; }
h4 { font-size: 1.15em; }
h5 { font-size: 1em; font-style: italic; }
h6 { font-size: 0.95em; font-style: italic; }

/* Primary text (paragraphs) with proper alignment */
p {
    margin: 0.8em 0;
    text-align: left;
    text-indent: 0;
    line-height: 1.6;
}

/* First paragraph after header - no indent */
h1 + p, h2 + p, h3 + p, h4 + p, h5 + p, h6 + p {
    text-indent: 0;
}

/* Secondary text (smaller, italics, etc.) */
.secondary, .subtitle, .author {
    text-align: center;
    font-style: italic;
    margin: 0.5em 0;
    color: #666;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
    page-break-inside: avoid;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    page-break-inside: avoid;
}

th, td {
    padding: 0.5em;
    border: 1px solid #ddd;
    text-align: left;
    vertical-align: top;
}

th {
    font-weight: bold;
    background-color: #f8f8f8;
}

pre, code {
    font-family: "Monaco", "Consolas", monospace;
    font-size: 0.9em;
    background: #f5f5f5;
    padding: 0.3em 0.5em;
    border-radius: 3px;
}

pre {
    margin: 1em 0;
    padding: 0.8em;
    border: 1px solid #e0e0e0;
    overflow-x: auto;
}

blockquote {
    margin: 1em 2em;
    font-style: italic;
    border-left: 3px solid #ccc;
    padding-left: 1em;
    page-break-inside: avoid;
}

/* Lists */
ul, ol {
    margin: 0.5em 0;
    padding-left: 2em;
}

li {
    margin: 0.3em 0;
}

/* Page breaks - improved */
.page-break, .pagebreak {
    page-break-before: always;
    margin: 0;
    padding: 0;
    height: 0;
}

.no-break {
    page-break-inside: avoid;
}

/* Avoid breaking after headers */
h1, h2, h3, h4, h5, h6 {
    break-after: avoid-page;
    page-break-after: avoid;
}

/* Cover page */
.cover-page {
    text-align: center;
    page-break-after: always;
}

.cover-page img {
    max-height: 90vh;
    max-width: 100%;
    width: auto;
    height: auto;
}

/* Section breaks */
.section-break {
    text-align: center;
    margin: 2em 0;
}

hr {
    border: 0;
    border-top: 1px solid #ddd;
    margin: 1.5em 0;
    page-break-after: avoid;
}
"""
    
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
    
    def create_enhanced_content_opf(self, is_kindle=False):
        """Create enhanced EPUB 3.3 content.opf file"""
        self.css = next(os.walk(self.css_path))[2]
        self.images = next(os.walk(self.images_path))[2]
        
        manifest = []
        spine = []
        
        # Add navigation document
        manifest.append("<item id=\"nav\" href=\"nav.xhtml\" media-type=\"application/xhtml+xml\" properties=\"nav\"/>")
        
        # Handle cover image and cover.xhtml
        cover_image_id = None
        cover_xhtml_id = None
        
        # Find cover image
        cover_images = [img for img in self.images if 'cover' in img.lower()]
        if cover_images:
            cover_img = cover_images[0]  # Use first cover image found
            dot_split = cover_img.split(".")
            cover_image_id = "cover-image"
            extension = dot_split[-1]
            media_type = "image/jpeg" if "jp" in extension else f"image/{extension}"
            manifest.append(f"<item id=\"{cover_image_id}\" href=\"Images/{cover_img}\" media-type=\"{media_type}\" properties=\"cover-image\"/>")
            
            # Create cover.xhtml
            cover_xhtml_id = "cover"
            self._create_cover_xhtml(cover_img, is_kindle)
            manifest.append(f"<item id=\"{cover_xhtml_id}\" href=\"cover.xhtml\" media-type=\"application/xhtml+xml\"/>")
            spine.insert(0, f"<itemref idref=\"{cover_xhtml_id}\"/>")
        
        for c in self.book_chapters:
            c["filename"] = c["filename"].replace(".html", ".xhtml")
            item_id = escape("".join(c["filename"].split(".")[:-1]))
            manifest.append("<item id=\"{0}\" href=\"{1}\" media-type=\"application/xhtml+xml\" />".format(
                item_id, c["filename"]
            ))
            spine.append("<itemref idref=\"{0}\"/>".format(item_id))
        
        for i in set(self.images):
            if i not in cover_images:  # Don't duplicate cover image
                dot_split = i.split(".")
                head = "img_" + escape("".join(dot_split[:-1]))
                extension = dot_split[-1]
                media_type = "image/jpeg" if "jp" in extension else f"image/{extension}"
                manifest.append("<item id=\"{0}\" href=\"Images/{1}\" media-type=\"{2}\" />".format(
                    head, i, media_type
                ))
        
        # Add enhanced CSS
        css_name = "kindle-style.css" if is_kindle else "standard-style.css"
        manifest.append(f"<item id=\"main-style\" href=\"Styles/{css_name}\" media-type=\"text/css\" />")
        
        authors = "\n".join("<dc:creator opf:file-as=\"{0}\" opf:role=\"aut\">{0}</dc:creator>".format(
            escape(aut.get("name", "n/d"))
        ) for aut in self.book_info.get("authors", []))
        
        subjects = "\n".join("<dc:subject>{0}</dc:subject>".format(escape(sub.get("name", "n/d")))
                             for sub in self.book_info.get("subjects", []))
        
        # Get current timestamp for dcterms:modified
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Use cover image ID for metadata
        cover_ref = cover_image_id if cover_image_id else ""
        
        return self.EPUB3_CONTENT_OPF.format(
            (self.book_info.get("isbn", self.book_info.get("identifier", ""))),
            escape(self.book_info.get("title", "")),
            authors,
            escape(self.book_info.get("description", "")),
            subjects,
            ", ".join(escape(pub.get("name", "")) for pub in self.book_info.get("publishers", [])),
            escape(self.book_info.get("rights", "")),
            self.book_info.get("issued", ""),
            cover_ref,
            current_time,
            "\n".join(manifest),
            "\n".join(spine),
            "cover.xhtml" if cover_xhtml_id else self.book_chapters[0]["filename"].replace(".html", ".xhtml")
        )
    
    def _create_cover_xhtml(self, cover_image, is_kindle=False):
        """Create a proper cover.xhtml file"""
        cover_css = """
        body {
            margin: 0;
            padding: 0;
            text-align: center;
            background-color: #000;
        }
        .cover-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            width: 100%;
        }
        .cover-image {
            max-width: 100%;
            max-height: 100vh;
            width: auto;
            height: auto;
            object-fit: contain;
        }
        """ if not is_kindle else """
        body {
            margin: 0;
            padding: 0;
            text-align: center;
            background-color: #000;
            font-family: "Times New Roman", serif;
        }
        .cover-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            width: 100%;
        }
        .cover-image {
            max-width: 100%;
            max-height: 100vh;
            width: auto;
            height: auto;
            object-fit: contain;
        }
        """
        
        cover_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Cover</title>
    <style type="text/css">
        {cover_css}
    </style>
</head>
<body>
    <div class="cover-container">
        <img src="Images/{cover_image}" alt="Cover" class="cover-image" />
    </div>
</body>
</html>"""
        
        with open(os.path.join(self.book_path, "OEBPS", "cover.xhtml"), "w", encoding="utf-8") as f:
            f.write(cover_xhtml)
    
    def create_navigation_document(self):
        """Create EPUB 3.3 navigation document"""
        nav_items = []
        for i, chapter in enumerate(self.book_chapters):
            filename = chapter["filename"].replace(".html", ".xhtml")
            title = escape(chapter["title"])
            nav_items.append(f'<li><a href="{filename}">{title}</a></li>')
        
        return self.EPUB3_NAV_XHTML.format("\n".join(nav_items))
    
    def create_enhanced_toc(self, api_url):
        """Create enhanced table of contents NCX file"""
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
        return self.EPUB3_TOC_NCX.format(
            (self.book_info["isbn"] if self.book_info["isbn"] else self.book_info.get("identifier", "")),
            max_depth,
            self.book_info.get("title", ""),
            ", ".join(aut.get("name", "") for aut in self.book_info.get("authors", [])),
            navmap
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
                sr, c, mx = EnhancedEpubGenerator.parse_toc(cc["children"], c, mx)
                r += sr
            
            r += "</navPoint>\n"
        
        return r, c, mx
    
    def create_enhanced_css(self, is_kindle=False):
        """Create enhanced CSS file"""
        css_content = self.KINDLE_CSS if is_kindle else self.STANDARD_CSS
        css_filename = "kindle-style.css" if is_kindle else "standard-style.css"
        
        with open(os.path.join(self.css_path, css_filename), 'w', encoding='utf-8') as f:
            f.write(css_content)
        
        return css_filename
    
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
        """Download image file with retry logic for reliability"""
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
            # Retry logic for failed downloads (max 3 attempts)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self._make_request(urljoin(SAFARI_BASE_URL, url), stream=True)
                    if response == 0:
                        if attempt < max_retries - 1:
                            self.display.log(f"Retry {attempt + 1}/{max_retries} for image: {image_name}")
                            continue
                        else:
                            self.display.error("Error trying to retrieve this image: %s\n    From: %s" % (image_name, url))
                            break
                    
                    with open(image_path, 'wb') as img:
                        for chunk in response.iter_content(1024):
                            img.write(chunk)
                    
                    # Success - break retry loop
                    break
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.display.log(f"Error downloading image (attempt {attempt + 1}/{max_retries}): {e}")
                        continue
                    else:
                        self.display.error(f"Failed to download image {image_name} after {max_retries} attempts: {e}")
        
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
    
    def create_enhanced_epub(self, api_url, book_id, path, is_kindle=False):
        """Create enhanced EPUB file with proper naming"""
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
            f.write(self.EPUB3_CONTAINER_XML.encode("utf-8", "xmlcharrefreplace"))
        
        # Create enhanced content.opf
        with open(os.path.join(self.book_path, "OEBPS", "content.opf"), "wb") as f:
            f.write(self.create_enhanced_content_opf(is_kindle).encode("utf-8", "xmlcharrefreplace"))
        
        # Create enhanced toc.ncx
        with open(os.path.join(self.book_path, "OEBPS", "toc.ncx"), "wb") as f:
            f.write(self.create_enhanced_toc(api_url).encode("utf-8", "xmlcharrefreplace"))
        
        # Create navigation document
        with open(os.path.join(self.book_path, "OEBPS", "nav.xhtml"), "wb") as f:
            f.write(self.create_navigation_document().encode("utf-8", "xmlcharrefreplace"))
        
        # Create enhanced CSS
        css_filename = self.create_enhanced_css(is_kindle)
        
        # Generate proper filename
        book_title = self.book_info.get("title", "Unknown Book")
        author = ", ".join(aut.get("name", "") for aut in self.book_info.get("authors", []))
        
        # Clean filename
        clean_title = "".join(c for c in book_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_author = "".join(c for c in author if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        if is_kindle:
            epub_filename = f"{clean_title} - {clean_author} (Kindle).epub"
        else:
            epub_filename = f"{clean_title} - {clean_author}.epub"
        
        # Create ZIP archive
        zip_file = os.path.join(path, "Books", book_id)
        if os.path.isfile(zip_file + ".zip"):
            os.remove(zip_file + ".zip")
        
        shutil.make_archive(zip_file, 'zip', self.book_path)
        
        # Rename with proper filename
        final_path = os.path.join(self.book_path, epub_filename)
        os.rename(zip_file + ".zip", final_path)
        
        return final_path
    
    def _make_request(self, url, **kwargs):
        """Make HTTP request using the session with timeout"""
        try:
            # Add timeout to prevent hanging (10s connect, 30s read)
            if 'timeout' not in kwargs:
                kwargs['timeout'] = (10, 30)
            
            if 'stream' in kwargs and kwargs['stream']:
                return self.session.get(url, stream=True, **{k: v for k, v in kwargs.items() if k != 'stream'})
            else:
                return self.session.get(url, **{k: v for k, v in kwargs.items() if k != 'stream'})
        except requests.exceptions.Timeout:
            self.display.error(f"Request timeout: {url}")
            return 0
        except Exception as e:
            self.display.error(f"Request error: {e}")
            return 0
