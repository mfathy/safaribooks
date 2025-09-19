# Authentication Module

This module provides robust authentication and session management for the SafariBooks scraper.

## Features

- **Cookie Management**: Load and validate cookies from configuration
- **Session Validation**: Test session validity with lightweight API calls
- **Error Handling**: Comprehensive custom exceptions for different error scenarios
- **Retry Logic**: Built-in retry strategy for network requests
- **Context Manager**: Use SessionManager as a context manager for automatic cleanup

## Quick Start

```python
from oreilly_scraper.auth import SessionManager, InvalidCookieError, SessionExpiredError

try:
    # Initialize with default configuration
    session_manager = SessionManager()
    
    # Get authenticated session
    session = session_manager.get_session()
    
    # Use session for requests
    response = session.get('https://learning.oreilly.com/profile/')
    
except InvalidCookieError:
    print("Cookies are missing or invalid")
except SessionExpiredError:
    print("Session has expired")
```

## Configuration

The SessionManager uses a YAML configuration file (`config/default_config.yaml`) with the following structure:

```yaml
auth:
  cookies_file: "cookies.json"
  urls:
    base_url: "https://learning.oreilly.com"
    profile_url: "https://learning.oreilly.com/profile/"
  session_validation:
    test_endpoint: "/profile/"
    timeout: 10
    max_retries: 3
```

## Custom Exceptions

- **`InvalidCookieError`**: Raised when cookies are missing, malformed, or invalid
- **`SessionExpiredError`**: Raised when the session has expired
- **`AuthenticationError`**: Raised when authentication fails
- **`ConfigurationError`**: Raised when configuration is invalid or missing

## Methods

### `get_session()`
Returns a ready-to-use authenticated session. This method:
1. Loads cookies from configuration
2. Creates a session with cookies
3. Validates the session
4. Returns the authenticated session

### `validate_session(session)`
Tests if a session is still valid by making a lightweight request to the configured endpoint.

### `refresh_session()`
Refreshes the current session by re-validating and potentially reloading cookies.

### `save_cookies(session, cookies_file)`
Saves session cookies to a file for persistence.

## Context Manager Usage

```python
with SessionManager() as session:
    # Use session for requests
    response = session.get('https://learning.oreilly.com/api/v1/book/123/')
    # Session is automatically closed when exiting the context
```

## Testing

Run the test suite:

```bash
python -m pytest tests/test_auth/test_session_manager.py -v
```

## Dependencies

- `PyYAML`: For configuration file parsing
- `requests`: For HTTP session management
- `urllib3`: For retry strategies

## Error Handling Best Practices

1. **Always catch specific exceptions** rather than using bare `except` clauses
2. **Handle `InvalidCookieError`** by prompting user to re-authenticate
3. **Handle `SessionExpiredError`** by refreshing the session or re-authenticating
4. **Use context managers** to ensure proper session cleanup
5. **Log authentication events** for debugging and monitoring

