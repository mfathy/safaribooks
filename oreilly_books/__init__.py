#!/usr/bin/env python3
# coding: utf-8
"""
OreillyBooks - Main Module
Orchestrates the book downloading process using modular components
"""

from .core import OreillyBooks
from .display import Display
from .auth import AuthManager
from .download import BookDownloader
from .epub_legacy import LegacyEpubGenerator
from .epub_enhanced import EnhancedEpubGenerator

__all__ = [
    'OreillyBooks',
    'Display', 
    'AuthManager',
    'BookDownloader',
    'LegacyEpubGenerator',
    'EnhancedEpubGenerator'
]
