"""
Session management for SafariBooks authentication.

This module provides the SessionManager class for handling authentication
sessions with O'Reilly's Safari Books Online platform.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Optional, Any
import yaml
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    InvalidCookieError,
    AuthenticationError,
    SessionExpiredError,
    ConfigurationError
)


class SessionManager:
    """
    Manages authentication sessions for SafariBooks scraper.
    
    This class handles:
    - Loading cookies from configuration
    - Creating authenticated requests.Session objects
    - Validating session validity
    - Managing session lifecycle
    
    Attributes:
        config (Dict[str, Any]): Configuration dictionary
        cookies_file (str): Path to cookies file
        session (Optional[requests.Session]): Current session object
        logger (logging.Logger): Logger instance
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize SessionManager.
        
        Args:
            config_path: Path to configuration file. If None, uses default.
            
        Raises:
            ConfigurationError: If configuration file cannot be loaded
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self.cookies_file = self._get_cookies_file_path()
        self.session: Optional[requests.Session] = None
        
        # Validate configuration
        self._validate_config()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        if config_path is None:
            # Use default config path
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "default_config.yaml"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.logger.debug(f"Loaded configuration from {config_path}")
                return config
        except FileNotFoundError:
            raise ConfigurationError(
                f"Configuration file not found: {config_path}",
                config_key="config_path"
            )
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in configuration file: {e}",
                config_key="yaml_parsing"
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration: {e}",
                config_key="file_loading"
            )
    
    def _get_cookies_file_path(self) -> str:
        """
        Get the full path to the cookies file.
        
        Returns:
            Full path to cookies file
        """
        cookies_file = self.config.get('auth', {}).get('cookies_file', 'cookies.json')
        
        # If it's an absolute path, use it as-is
        if os.path.isabs(cookies_file):
            return cookies_file
        
        # Otherwise, make it relative to project root
        project_root = Path(__file__).parent.parent.parent
        return str(project_root / cookies_file)
    
    def _validate_config(self) -> None:
        """
        Validate that required configuration keys are present.
        
        Raises:
            ConfigurationError: If required configuration is missing
        """
        required_keys = [
            'auth.urls.base_url',
            'auth.urls.profile_url',
            'auth.session_validation.test_endpoint'
        ]
        
        for key in required_keys:
            keys = key.split('.')
            current = self.config
            
            try:
                for k in keys:
                    current = current[k]
            except (KeyError, TypeError):
                raise ConfigurationError(
                    f"Required configuration key missing: {key}",
                    config_key=key
                )
    
    def _load_cookies(self) -> Dict[str, str]:
        """
        Load cookies from the cookies file.
        
        Returns:
            Dictionary of cookies
            
        Raises:
            InvalidCookieError: If cookies cannot be loaded or are invalid
        """
        if not os.path.exists(self.cookies_file):
            raise InvalidCookieError(
                f"Cookies file not found: {self.cookies_file}",
                cookie_file=self.cookies_file
            )
        
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                
            if not isinstance(cookies, dict):
                raise InvalidCookieError(
                    f"Invalid cookies format: expected dict, got {type(cookies)}",
                    cookie_file=self.cookies_file
                )
            
            if not cookies:
                raise InvalidCookieError(
                    "Cookies file is empty",
                    cookie_file=self.cookies_file
                )
            
            self.logger.debug(f"Loaded {len(cookies)} cookies from {self.cookies_file}")
            return cookies
            
        except json.JSONDecodeError as e:
            raise InvalidCookieError(
                f"Invalid JSON in cookies file: {e}",
                cookie_file=self.cookies_file
            )
        except Exception as e:
            raise InvalidCookieError(
                f"Failed to load cookies: {e}",
                cookie_file=self.cookies_file
            )
    
    def _create_session(self, cookies: Dict[str, str]) -> requests.Session:
        """
        Create a requests.Session with cookies and proper configuration.
        
        Args:
            cookies: Dictionary of cookies to attach
            
        Returns:
            Configured requests.Session object
        """
        session = requests.Session()
        
        # Set cookies
        session.cookies.update(cookies)
        
        # Set headers
        user_agent = self.config.get('download', {}).get('user_agent', 
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.get('auth', {}).get('session_validation', {}).get('max_retries', 3),
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        self.logger.debug("Created new session with cookies and retry strategy")
        return session
    
    def validate_session(self, session: Optional[requests.Session] = None) -> bool:
        """
        Validate that the session is still active and cookies are valid.
        
        This method makes a lightweight request to test session validity.
        
        Args:
            session: Session to validate. If None, uses current session.
            
        Returns:
            True if session is valid, False otherwise
            
        Raises:
            SessionExpiredError: If session validation fails
        """
        if session is None:
            session = self.session
        
        if session is None:
            raise SessionExpiredError("No session to validate")
        
        try:
            # Get validation endpoint from config
            base_url = self.config['auth']['urls']['base_url']
            test_endpoint = self.config['auth']['session_validation']['test_endpoint']
            timeout = self.config['auth']['session_validation']['timeout']
            
            test_url = f"{base_url}{test_endpoint}"
            
            self.logger.debug(f"Validating session with endpoint: {test_url}")
            
            response = session.get(
                test_url,
                timeout=timeout,
                allow_redirects=False
            )
            
            # Check for successful response
            if response.status_code == 200:
                # Additional check for expired subscription
                if "user_type\":\"Expired\"" in response.text:
                    raise SessionExpiredError("Account subscription has expired")
                
                self.logger.debug("Session validation successful")
                return True
            
            elif response.status_code in [401, 403]:
                raise SessionExpiredError(f"Session expired (HTTP {response.status_code})")
            
            else:
                self.logger.warning(f"Unexpected response code during validation: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            raise SessionExpiredError(f"Session validation failed: {e}")
        except Exception as e:
            raise SessionExpiredError(f"Unexpected error during session validation: {e}")
    
    def get_session(self) -> requests.Session:
        """
        Get a ready-to-use authenticated session.
        
        This method:
        1. Loads cookies from configuration
        2. Creates a session with cookies
        3. Validates the session
        4. Returns the authenticated session
        
        Returns:
            Authenticated requests.Session object
            
        Raises:
            InvalidCookieError: If cookies are missing or invalid
            SessionExpiredError: If session validation fails
        """
        try:
            # Load cookies
            cookies = self._load_cookies()
            
            # Create session
            session = self._create_session(cookies)
            
            # Validate session
            self.validate_session(session)
            
            # Store session for reuse
            self.session = session
            
            self.logger.info("Successfully created and validated authenticated session")
            return session
            
        except (InvalidCookieError, SessionExpiredError):
            # Re-raise these exceptions as-is
            raise
        except Exception as e:
            raise AuthenticationError(f"Failed to create authenticated session: {e}")
    
    def refresh_session(self) -> requests.Session:
        """
        Refresh the current session by re-validating and potentially reloading cookies.
        
        Returns:
            Refreshed authenticated session
            
        Raises:
            InvalidCookieError: If cookies are missing or invalid
            SessionExpiredError: If session cannot be refreshed
        """
        self.logger.info("Refreshing session")
        
        # Clear current session
        self.session = None
        
        # Get new session
        return self.get_session()
    
    def save_cookies(self, session: requests.Session, cookies_file: Optional[str] = None) -> None:
        """
        Save session cookies to file.
        
        Args:
            session: Session containing cookies to save
            cookies_file: Path to save cookies. If None, uses configured path.
            
        Raises:
            ConfigurationError: If cookies cannot be saved
        """
        if cookies_file is None:
            cookies_file = self.cookies_file
        
        try:
            cookies_dict = session.cookies.get_dict()
            
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies_dict, f, indent=2)
            
            self.logger.info(f"Saved {len(cookies_dict)} cookies to {cookies_file}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save cookies: {e}")
    
    def close_session(self) -> None:
        """Close the current session and clean up resources."""
        if self.session:
            self.session.close()
            self.session = None
            self.logger.debug("Session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self.get_session()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_session()

