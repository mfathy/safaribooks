#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom Exceptions for OreillyBooks
Handles recoverable download errors without terminating the entire process
"""


class BookDownloadError(Exception):
    """Exception raised when a book download fails but the process should continue"""
    
    def __init__(self, message, book_id=None, book_title=None, url=None, original_error=None):
        super().__init__(message)
        self.book_id = book_id
        self.book_title = book_title
        self.url = url
        self.original_error = original_error
    
    def __str__(self):
        base_msg = super().__str__()
        if self.book_title:
            return f"{base_msg} (Book: {self.book_title})"
        return base_msg
