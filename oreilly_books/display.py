#!/usr/bin/env python3
# coding: utf-8
"""
Display and Logging Module for SafariBooks
Handles all user interface, logging, and progress reporting
"""

import os
import sys
import shutil
import logging
import traceback
import random
from multiprocessing import Value
from lxml import html


class Display:
    """Display and logging management with unified component-based logging"""
    
    # Unified format: [HH:MM:SS] [COMPONENT] [LEVEL] Message
    BASE_FORMAT = logging.Formatter(
        fmt="[%(asctime)s] [%(component)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    SH_DEFAULT = "\033[0m" if "win" not in sys.platform else ""
    SH_YELLOW = "\033[33m" if "win" not in sys.platform else ""
    SH_BG_RED = "\033[41m" if "win" not in sys.platform else ""
    SH_BG_YELLOW = "\033[43m" if "win" not in sys.platform else ""

    def __init__(self, log_file, path, component="Display"):
        self.path = path
        self.output_dir = ""
        self.output_dir_set = False
        self.default_component = component  # Default component name
        
        # Ensure logs directory exists
        log_path = os.path.join(path, "logs", log_file)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.log_file = log_path

        # Create logger with custom adapter for component support
        self.logger = logging.getLogger("SafariBooks")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers = []
        
        # File handler
        file_handler = logging.FileHandler(filename=self.log_file)
        file_handler.setFormatter(self.BASE_FORMAT)
        file_handler.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        
        # Console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self.BASE_FORMAT)
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)

        self.columns, _ = shutil.get_terminal_size()
        
        # Log welcome message with component
        self._log_with_component("INFO", "** Welcome to SafariBooks! **", self.default_component)

        self.book_ad_info = False
        self.css_ad_info = Value("i", 0)
        self.images_ad_info = Value("i", 0)
        self.last_request = (None,)
        self.in_error = False
        self.state_status = Value("i", 0)
        sys.excepthook = self.unhandled_exception
    
    def _log_with_component(self, level, message, component=None):
        """Internal method to log with component context"""
        if component is None:
            component = self.default_component
        
        # Create a logging adapter that adds component context
        extra = {'component': component}
        getattr(self.logger, level.lower())(message, extra=extra)

    def set_output_dir(self, output_dir):
        self.info("Output directory:\n    %s" % output_dir)
        self.output_dir = output_dir
        self.output_dir_set = True

    def unregister(self):
        self.logger.handlers[0].close()
        sys.excepthook = sys.__excepthook__

    def log(self, message, component=None):
        """Log a message with optional component tag"""
        try:
            msg = str(message, "utf-8", "replace")
        except (UnicodeDecodeError, Exception):
            msg = str(message)
        self._log_with_component("INFO", msg, component)

    def out(self, put):
        """Legacy method - now logs through logger instead of direct stdout"""
        # For backwards compatibility, but prefer using log() directly
        pattern = "\r{!s}\r{!s}\n"
        try:
            s = pattern.format(" " * self.columns, str(put, "utf-8", "replace"))
        except TypeError:
            s = pattern.format(" " * self.columns, put)
        # Still write to stdout for backwards compatibility, but main logging goes through logger
        sys.stdout.write(s)

    def info(self, message, state=False, component=None):
        """Log an info message with optional component tag"""
        self.log(message, component)
        # For visual indicators in console, we can keep some formatting but main log goes through logger
        if state:
            # This is for important status messages
            pass  # Already logged via self.log()

    def error(self, error, component=None):
        """Log an error message with optional component tag"""
        if not self.in_error:
            self.in_error = True
        try:
            msg = str(error, "utf-8", "replace")
        except (UnicodeDecodeError, Exception):
            msg = str(error)
        self._log_with_component("ERROR", msg, component)

    def exit(self, error, raise_exception=False):
        self.error(str(error))
        if self.output_dir_set:
            output = (self.SH_YELLOW + "[+]" + self.SH_DEFAULT +
                      " Please delete the output directory '" + self.output_dir + "'"
                      " and restart the program.")
            self.out(output)
        
        if raise_exception:
            # Import here to avoid circular imports
            from oreilly_books.exceptions import BookDownloadError
            self.save_last_request()
            raise BookDownloadError(str(error))
        else:
            output = self.SH_BG_RED + "[!]" + self.SH_DEFAULT + " Aborting..."
            self.out(output)
            self.save_last_request()
            sys.exit(1)

    def unhandled_exception(self, _, o, tb):
        self.log("".join(traceback.format_tb(tb)), component="Exception")
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
""" if random.random() > 0.5 else r"""
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
            self.log("Error parsing the description: %s" % e, component="Parser")
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
                  "        https://learning.oreilly.com\n\n" +
                  self.SH_BG_RED + "[!]" + self.SH_DEFAULT + " Bye!!")

    @staticmethod
    def api_error(response):
        from config import SAFARI_BASE_URL, COOKIES_FILE
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
