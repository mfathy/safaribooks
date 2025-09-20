"""
Authentication module for Oreilly scraper.

This module provides authentication and session management functionality
for interacting with O'Reilly's Safari Books Online platform.
"""

from .session_manager import SessionManager
from .exceptions import (
    InvalidCookieError,
    AuthenticationError,
    SessionExpiredError,
    ConfigurationError
)

__all__ = [
    'SessionManager',
    'InvalidCookieError',
    'AuthenticationError', 
    'SessionExpiredError',
    'ConfigurationError'
]

