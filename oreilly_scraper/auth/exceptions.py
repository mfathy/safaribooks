"""
Custom exceptions for the authentication module.

This module defines custom exception classes for handling various
authentication and session management errors.
"""


class SafariBooksAuthError(Exception):
    """Base exception class for all SafariBooks authentication errors."""
    pass


class InvalidCookieError(SafariBooksAuthError):
    """
    Raised when cookies are missing, malformed, or invalid.
    
    This exception is raised when:
    - Cookie file doesn't exist
    - Cookie file is empty or corrupted
    - Required cookies are missing
    - Cookie format is invalid
    """
    
    def __init__(self, message: str, cookie_file: str = None):
        super().__init__(message)
        self.cookie_file = cookie_file


class AuthenticationError(SafariBooksAuthError):
    """
    Raised when authentication fails.
    
    This exception is raised when:
    - Login credentials are invalid
    - Authentication request fails
    - Server returns authentication error
    """
    pass


class SessionExpiredError(SafariBooksAuthError):
    """
    Raised when the session has expired.
    
    This exception is raised when:
    - Session validation fails
    - Server returns session expired response
    - Cookies are no longer valid
    """
    
    def __init__(self, message: str, session_id: str = None):
        super().__init__(message)
        self.session_id = session_id


class ConfigurationError(SafariBooksAuthError):
    """
    Raised when configuration is invalid or missing.
    
    This exception is raised when:
    - Configuration file doesn't exist
    - Required configuration keys are missing
    - Configuration values are invalid
    """
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message)
        self.config_key = config_key

