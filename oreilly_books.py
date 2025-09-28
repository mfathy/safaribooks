#!/usr/bin/env python3
# coding: utf-8
"""
OreillyBooks - Main Entry Point
Command-line interface for downloading O'Reilly books
"""

import sys
import argparse
from oreilly_books import OreillyBooks


def main():
    """Main entry point"""
    arguments = argparse.ArgumentParser(prog="oreilly_books.py",
                                        description="Download and generate an EPUB of your favorite books"
                                                    " from O'Reilly Learning.",
                                        add_help=False,
                                        allow_abbrev=False)
    
    login_arg_group = arguments.add_mutually_exclusive_group()
    login_arg_group.add_argument(
        "--cred", metavar="<EMAIL:PASS>", default=False,
        help="Credentials used to perform the auth login on O'Reilly Learning."
             " Es. ` --cred \"account_mail@mail.com:password01\" `."
    )
    login_arg_group.add_argument(
        "--login", action='store_true',
        help="Prompt for credentials used to perform the auth login on O'Reilly Learning."
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
    arguments.add_argument(
        "--help", action='store_true', help="Show this help message."
    )
    
    arguments.add_argument(
        "bookid", nargs='?', help="Book digits ID that you want to download. You can find"
                                  " it in the URL (X-es):"
                                  " `https://learning.oreilly.com/library/view/book-name/XXXXXXXXXXXXX/`"
    )
    
    args_parsed = arguments.parse_args()
    
    if args_parsed.help or not args_parsed.bookid:
        arguments.print_help()
        sys.exit(0)
    
    if args_parsed.cred or args_parsed.login:
        print("WARNING: Due to recent changes on ORLY website, \n" \
                "the `--cred` and `--login` options are temporarily disabled.\n"
                "    Please use the `cookies.json` file to authenticate your account.\n"
                "    See: https://github.com/lorenzodifuccia/safaribooks/issues/358")
        arguments.exit()
    else:
        if args_parsed.no_cookies:
            arguments.error("invalid option: `--no-cookies` is valid only if you use the `--cred` option")
    
    OreillyBooks(args_parsed)
    sys.exit(0)


if __name__ == "__main__":
    main()
