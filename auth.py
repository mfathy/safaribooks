#!/usr/bin/env python3
# coding: utf-8
"""
Authentication Module for SafariBooks
Handles login, session management, and cookie operations
"""

import os
import json
import requests
import re
from urllib.parse import urlparse, parse_qs, quote_plus
from lxml import html
from config import (
    COOKIES_FILE, LOGIN_URL, LOGIN_ENTRY_URL, API_ORIGIN_URL, 
    PROFILE_URL, HEADERS
)


class AuthManager:
    """Handles authentication and session management for SafariBooks"""
    
    COOKIE_FLOAT_MAX_AGE_PATTERN = re.compile(r'(max-age=\d*\.\d*)', re.IGNORECASE)
    
    def __init__(self, display):
        self.display = display
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.jwt = {}
    
    def handle_cookie_update(self, set_cookie_headers):
        """Handle cookie updates from response headers"""
        for morsel in set_cookie_headers:
            if self.COOKIE_FLOAT_MAX_AGE_PATTERN.search(morsel):
                cookie_key, cookie_value = morsel.split(";")[0].split("=")
                self.session.cookies.set(cookie_key, cookie_value)
    
    def requests_provider(self, url, is_post=False, data=None, perform_redirect=True, **kwargs):
        """Make HTTP requests with proper error handling and cookie management"""
        try:
            response = getattr(self.session, "post" if is_post else "get")(
                url, data=data, allow_redirects=False, **kwargs
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
    
    @staticmethod
    def parse_cred(cred):
        """Parse credentials from string format"""
        if ":" not in cred:
            return False
        sep = cred.index(":")
        new_cred = ["", ""]
        new_cred[0] = cred[:sep].strip("'").strip('"')
        if "@" not in new_cred[0]:
            return False
        new_cred[1] = cred[sep + 1:]
        return new_cred
    
    def do_login(self, email, password):
        """Perform login to Safari Books Online"""
        response = self.requests_provider(LOGIN_ENTRY_URL)
        if response == 0:
            self.display.exit("Login: unable to reach Safari Books Online. Try again...")
        
        next_parameter = None
        try:
            next_parameter = parse_qs(urlparse(response.request.url).query)["next"][0]
        except (AttributeError, ValueError, IndexError):
            self.display.exit("Login: unable to complete login on Safari Books Online. Try again...")
        
        redirect_uri = API_ORIGIN_URL + quote_plus(next_parameter)
        response = self.requests_provider(
            LOGIN_URL, is_post=True, json={
                "email": email, "password": password, "redirect_uri": redirect_uri
            }, perform_redirect=False
        )
        
        if response == 0:
            self.display.exit("Login: unable to perform auth to Safari Books Online.\n    Try again...")
        
        if response.status_code != 200:
            try:
                error_page = html.fromstring(response.text)
                errors_message = error_page.xpath("//ul[@class='errorlist']//li/text()")
                recaptcha = error_page.xpath("//div[@class='g-recaptcha']")
                messages = (["    `%s`" % error for error in errors_message
                             if "password" in error or "email" in error] if len(errors_message) else []) + \
                           (["    `ReCaptcha required (wait or do logout from the website).`"] if len(recaptcha) else [])
                self.display.exit(
                    "Login: unable to perform auth login to Safari Books Online.\n" + self.display.SH_YELLOW +
                    "[*]" + self.display.SH_DEFAULT + " Details:\n" + "%s" % "\n".join(
                        messages if len(messages) else ["    Unexpected error!"])
                )
            except (html.etree.ParseError, html.etree.ParserError) as parsing_error:
                self.display.error(parsing_error)
                self.display.exit(
                    "Login: your login went wrong and it encountered in an error"
                    " trying to parse the login details of Safari Books Online. Try again..."
                )
        
        self.jwt = response.json()
        response = self.requests_provider(self.jwt["redirect_uri"])
        if response == 0:
            self.display.exit("Login: unable to reach Safari Books Online. Try again...")
    
    def check_login(self):
        """Verify if the current session is valid"""
        response = self.requests_provider(PROFILE_URL, perform_redirect=False)
        if response == 0:
            self.display.exit("Login: unable to reach Safari Books Online. Try again...")
        elif response.status_code != 200:
            self.display.exit("Authentication issue: unable to access profile page.")
        elif "user_type\":\"Expired\"" in response.text:
            self.display.exit("Authentication issue: account subscription expired.")
        self.display.info("Successfully authenticated.", state=True)
    
    def load_cookies(self):
        """Load cookies from file"""
        if not os.path.isfile(COOKIES_FILE):
            self.display.exit("Login: unable to find `cookies.json` file.\n"
                              "    Please use the `--cred` or `--login` options to perform the login.")
        self.session.cookies.update(json.load(open(COOKIES_FILE)))
    
    def save_cookies(self):
        """Save cookies to file"""
        json.dump(self.session.cookies.get_dict(), open(COOKIES_FILE, 'w'))
    
    def initialize_session(self, cred=None, no_cookies=False):
        """Initialize session with authentication"""
        if not cred:
            self.load_cookies()
        else:
            self.display.info("Logging into Safari Books Online...", state=True)
            self.do_login(*cred)
            if not no_cookies:
                self.save_cookies()
        self.check_login()
        return self.session
