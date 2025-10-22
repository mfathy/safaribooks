# Token Invalidation Fix

## Problem Summary

The `download_books.py` script was invalidating O'Reilly authentication tokens quickly, while `safaribooks.py` worked fine when downloading books in a bash loop.

## Root Cause Analysis

### How safaribooks.py Works (Correctly)
1. Creates **ONE session** at initialization
2. **Reuses the same session** for all requests throughout the book download
3. **Updates cookies in real-time** from every HTTP response via `handle_cookie_update()`
4. **Saves updated cookies** to `cookies.json` before exiting
5. When run in a bash loop, each invocation gets fresh cookies from the previous run

### How download_books.py Worked (Incorrectly - BEFORE FIX)
1. Created a **NEW `OreillyBooks()` instance** for each book
2. Each instance created a **fresh session** from `cookies.json`
3. Every book started with the **ORIGINAL cookies** (not refreshed ones)
4. No cookie updates were propagated between book downloads
5. Server detected multiple sessions using the same stale token → **Token invalidation**

## The Fix

### Key Changes Made

#### 1. Shared Session Management
```python
# In BookDownloader.__init__()
self.display = Display("batch_download.log", PATH)
self.auth_manager = AuthManager(self.display)
self.session = self.auth_manager.initialize_session()  # ONE session for all books
self.books_downloaded_since_save = 0
```

#### 2. Cookie Update Mechanism
Added the same cookie handling that `safaribooks.py` uses:
```python
def _update_cookies_from_response(self, response):
    """Update session cookies from response headers (like safaribooks.py does)"""
    if hasattr(response, 'raw') and hasattr(response.raw, 'headers'):
        set_cookie_headers = response.raw.headers.getlist("Set-Cookie")
        for morsel in set_cookie_headers:
            if self.COOKIE_FLOAT_MAX_AGE_PATTERN.search(morsel):
                cookie_key, cookie_value = morsel.split(";")[0].split("=", 1)
                self.session.cookies.set(cookie_key, cookie_value)
```

#### 3. Periodic Cookie Persistence
```python
# Save cookies every 5 books to keep them fresh
self.books_downloaded_since_save += 1
if self.books_downloaded_since_save >= 5:
    self._save_cookies()
    self.books_downloaded_since_save = 0
```

#### 4. Final Cookie Save
```python
# At the end of download_all_books()
self._save_cookies()
self.logger.info("Session cookies saved to file")
```

#### 5. Rewritten download_single_book()
Instead of creating a new `OreillyBooks()` instance:
```python
# OLD (BROKEN):
OreillyBooks(args)  # Creates new session, loads stale cookies

# NEW (FIXED):
internal_downloader = InternalDownloader(self.session, self.display, args.bookid)
# Uses the shared session that maintains fresh cookies
```

## Why This Works

### Token Refresh Flow
1. **Initial Request**: Uses token from `cookies.json`
2. **Response**: Server sends refreshed token in `Set-Cookie` header
3. **Session Update**: New token is immediately stored in the session
4. **Next Request**: Uses the fresh token (not the stale one from file)
5. **Periodic Save**: Fresh token is saved to `cookies.json` every 5 books
6. **Final Save**: Latest token state saved when script completes

### Security Perspective
O'Reilly's API likely uses:
- **Short-lived JWT tokens** (`orm-jwt` cookie)
- **Session identifiers** (`orm-rt` cookie)
- **Anti-bot tokens** (`_abck`, `bm_sv` cookies)

These tokens are designed to:
- Expire after a certain time
- Get refreshed with each valid request
- Detect reuse of the same token across multiple sessions (suspicious behavior)

**Before the fix**: Each book used the same initial token → Server flagged as bot behavior → Token invalidated

**After the fix**: Each book uses a progressively refreshed token → Normal user behavior → Tokens remain valid

## Technical Details

### Cookie Update Pattern
The `COOKIE_FLOAT_MAX_AGE_PATTERN` regex specifically handles cookies with float max-age values:
```python
COOKIE_FLOAT_MAX_AGE_PATTERN = re.compile(r'(max-age=\d*\.\d*)', re.IGNORECASE)
```

This is important because some O'Reilly cookies use fractional seconds in their expiration.

### Session Reuse Benefits
1. **Token Freshness**: Cookies get updated automatically
2. **Connection Pooling**: HTTP connections are reused (faster)
3. **Rate Limiting Compliance**: Appears as one continuous session
4. **Anti-Bot Evasion**: Normal user behavior pattern

### Import Changes
Added imports for the modular architecture:
```python
from oreilly_books.core import OreillyBooks
from oreilly_books.auth import AuthManager
from oreilly_books.display import Display
from config import COOKIES_FILE, PATH
```

## Migration Notes

### No Changes Required for Users
- Existing `cookies.json` files still work
- Configuration files unchanged
- Command-line interface identical
- Progress tracking still functional

### Performance Impact
- **Slightly faster**: Connection pooling, no repeated authentication
- **More reliable**: No token invalidation issues
- **Same rate limiting**: Still respects `download_delay` config

## Testing Recommendations

1. **Single Book Test**: Download one book to verify basic functionality
2. **Multi-Book Test**: Download 10+ books to verify session persistence
3. **Long Session Test**: Download 50+ books to verify cookie refresh cycle
4. **Resume Test**: Stop and restart to verify cookies are properly saved

## Comparison with safaribooks.py

| Feature | safaribooks.py | download_books.py (BEFORE) | download_books.py (AFTER) |
|---------|----------------|----------------------------|---------------------------|
| Session creation | Once per script | Once per book | Once per script ✓ |
| Cookie updates | Every request | Never | Every request ✓ |
| Cookie persistence | On exit | Never | Every 5 books + on exit ✓ |
| Token freshness | Always fresh | Stale after first book | Always fresh ✓ |
| Multi-book reliability | High | Low (tokens invalidate) | High ✓ |

## Related Files Modified

- `download_books.py`: Complete rewrite of session management
- `docs/TOKEN_INVALIDATION_FIX.md`: This documentation

## References

- Original `safaribooks.py`: Lines 312-449 (session and cookie management)
- `oreilly_books/auth.py`: Lines 38-67 (cookie update mechanism)
- `download_books.py`: Lines 29-58 (new initialization), 193-214 (cookie helpers), 216-364 (rewritten download method)

## Conclusion

The fix transforms `download_books.py` from creating ephemeral sessions (like separate bash script invocations) to maintaining a persistent session (like `safaribooks.py` does internally). This aligns with how O'Reilly's API expects clients to behave and prevents token invalidation.

