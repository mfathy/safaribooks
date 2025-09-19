"""
Tests for SessionManager class.

This module contains unit tests for the SessionManager authentication class.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
import requests

# Add the project root to the path so we can import our modules
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from oreilly_scraper.auth.session_manager import SessionManager
from oreilly_scraper.auth.exceptions import (
    InvalidCookieError,
    SessionExpiredError,
    ConfigurationError
)


class TestSessionManager(unittest.TestCase):
    """Test cases for SessionManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yaml")
        self.cookies_file = os.path.join(self.temp_dir, "test_cookies.json")
        
        # Create test configuration
        self.test_config = {
            'auth': {
                'cookies_file': 'test_cookies.json',
                'urls': {
                    'base_url': 'https://learning.oreilly.com',
                    'profile_url': 'https://learning.oreilly.com/profile/',
                    'login_url': 'https://www.oreilly.com/member/auth/login/',
                    'login_entry_url': 'https://learning.oreilly.com/login/unified/?next=/home/'
                },
                'session_validation': {
                    'test_endpoint': '/profile/',
                    'timeout': 10,
                    'max_retries': 3
                }
            },
            'download': {
                'user_agent': 'Test User Agent'
            }
        }
        
        # Write test config to file
        import yaml
        with open(self.config_file, 'w') as f:
            yaml.dump(self.test_config, f)
        
        # Create test cookies
        self.test_cookies = {
            'sessionid': 'test_session_id',
            'csrftoken': 'test_csrf_token',
            'auth_token': 'test_auth_token'
        }
        
        with open(self.cookies_file, 'w') as f:
            json.dump(self.test_cookies, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_init_with_valid_config(self):
        """Test SessionManager initialization with valid config."""
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            manager = SessionManager(self.config_file)
            self.assertIsNotNone(manager.config)
            self.assertEqual(manager.cookies_file, self.cookies_file)
    
    def test_init_with_missing_config(self):
        """Test SessionManager initialization with missing config file."""
        with self.assertRaises(ConfigurationError):
            SessionManager("/nonexistent/config.yaml")
    
    def test_load_cookies_success(self):
        """Test successful cookie loading."""
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            manager = SessionManager(self.config_file)
            cookies = manager._load_cookies()
            
            self.assertEqual(cookies, self.test_cookies)
    
    def test_load_cookies_file_not_found(self):
        """Test cookie loading when file doesn't exist."""
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            # Remove cookies file
            os.remove(self.cookies_file)
            
            manager = SessionManager(self.config_file)
            
            with self.assertRaises(InvalidCookieError):
                manager._load_cookies()
    
    def test_load_cookies_invalid_json(self):
        """Test cookie loading with invalid JSON."""
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            # Write invalid JSON
            with open(self.cookies_file, 'w') as f:
                f.write("invalid json content")
            
            manager = SessionManager(self.config_file)
            
            with self.assertRaises(InvalidCookieError):
                manager._load_cookies()
    
    def test_load_cookies_empty_file(self):
        """Test cookie loading with empty file."""
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            # Write empty file
            with open(self.cookies_file, 'w') as f:
                f.write("")
            
            manager = SessionManager(self.config_file)
            
            with self.assertRaises(InvalidCookieError):
                manager._load_cookies()
    
    def test_create_session(self):
        """Test session creation with cookies."""
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            manager = SessionManager(self.config_file)
            session = manager._create_session(self.test_cookies)
            
            self.assertIsInstance(session, requests.Session)
            self.assertEqual(session.cookies.get_dict(), self.test_cookies)
            self.assertIn('Test User Agent', session.headers['User-Agent'])
    
    @patch('requests.Session.get')
    def test_validate_session_success(self, mock_get):
        """Test successful session validation."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"user_type": "Active"}'
        mock_get.return_value = mock_response
        
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            manager = SessionManager(self.config_file)
            session = manager._create_session(self.test_cookies)
            
            result = manager.validate_session(session)
            self.assertTrue(result)
    
    @patch('requests.Session.get')
    def test_validate_session_expired(self, mock_get):
        """Test session validation with expired session."""
        # Mock expired response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            manager = SessionManager(self.config_file)
            session = manager._create_session(self.test_cookies)
            
            with self.assertRaises(SessionExpiredError):
                manager.validate_session(session)
    
    @patch('requests.Session.get')
    def test_validate_session_subscription_expired(self, mock_get):
        """Test session validation with expired subscription."""
        # Mock expired subscription response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"user_type": "Expired"}'
        mock_get.return_value = mock_response
        
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            manager = SessionManager(self.config_file)
            session = manager._create_session(self.test_cookies)
            
            with self.assertRaises(SessionExpiredError) as cm:
                manager.validate_session(session)
            
            self.assertIn("subscription has expired", str(cm.exception))
    
    @patch('requests.Session.get')
    def test_get_session_success(self, mock_get):
        """Test successful session retrieval."""
        # Mock successful validation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"user_type": "Active"}'
        mock_get.return_value = mock_response
        
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            manager = SessionManager(self.config_file)
            session = manager.get_session()
            
            self.assertIsInstance(session, requests.Session)
            self.assertEqual(session.cookies.get_dict(), self.test_cookies)
    
    def test_get_session_invalid_cookies(self):
        """Test session retrieval with invalid cookies."""
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            # Remove cookies file
            os.remove(self.cookies_file)
            
            manager = SessionManager(self.config_file)
            
            with self.assertRaises(InvalidCookieError):
                manager.get_session()
    
    def test_save_cookies(self):
        """Test saving cookies to file."""
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            manager = SessionManager(self.config_file)
            session = manager._create_session(self.test_cookies)
            
            # Save cookies to a new file
            new_cookies_file = os.path.join(self.temp_dir, "new_cookies.json")
            manager.save_cookies(session, new_cookies_file)
            
            # Verify cookies were saved
            self.assertTrue(os.path.exists(new_cookies_file))
            with open(new_cookies_file, 'r') as f:
                saved_cookies = json.load(f)
            self.assertEqual(saved_cookies, self.test_cookies)
    
    def test_context_manager(self):
        """Test SessionManager as context manager."""
        with patch('oreilly_scraper.auth.session_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path(self.temp_dir)
            
            with patch('requests.Session.get') as mock_get:
                # Mock successful validation
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = '{"user_type": "Active"}'
                mock_get.return_value = mock_response
                
                manager = SessionManager(self.config_file)
                
                with manager as session:
                    self.assertIsInstance(session, requests.Session)
                    self.assertEqual(session.cookies.get_dict(), self.test_cookies)
                
                # Session should be closed after context exit
                self.assertIsNone(manager.session)


if __name__ == '__main__':
    unittest.main()

