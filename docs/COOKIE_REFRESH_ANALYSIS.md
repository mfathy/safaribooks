# Cookie Refresh Token Problem - Deep Analysis

## Current Situation

The `download_books.py` script is returning JSON parsing errors:
```
"Expecting value: line 1 column 1 (char 0)"
```

This error means the O'Reilly API is returning **HTML (login page) instead of JSON**, indicating **authentication has failed**.

## Root Cause

The previous fix added:
1. ✅ Shared session across all downloads
2. ✅ `_update_cookies_from_response()` method
3. ❌ **BUT the method is NEVER CALLED!**

### The Problem Flow

```python
# download_books.py line 266-302
internal_downloader = InternalDownloader(self.session, ...)
book_info_data = internal_downloader.get_book_info()  # <-- Makes HTTP request
# ❌ BUT cookies from response are NEVER extracted!
```

The `InternalDownloader` from `oreilly_books/download.py` makes HTTP requests using the shared session, but:
- The responses contain updated cookies from O'Reilly
- These cookies are **not being extracted and saved**
- On subsequent requests, the **stale cookies cause authentication to fail**

### How safaribooks.py Does It Correctly

```python
# safaribooks.py line 432
response = self.session.get(url, ...)
self.handle_cookie_update(response.raw.headers.getlist("Set-Cookie"))  # <-- Updates cookies!
```

**After EVERY HTTP request**, `safaribooks.py`:
1. Extracts `Set-Cookie` headers from the response
2. Updates the session cookies
3. This keeps authentication fresh

## The Real Solution

We have two options:

### Option 1: Patch `oreilly_books/download.py` (Better)
Modify the `InternalDownloader` class to update cookies after each request, just like `safaribooks.py` does.

### Option 2: Wrapper Approach (Simpler but less elegant)
Create a wrapper around the session that auto-updates cookies on every request.

## Recommendation

**Option 1** is better because:
- It fixes the problem at the source
- All future code using `InternalDownloader` will benefit
- It matches the proven pattern from `safaribooks.py`

The fix requires modifying `/Users/mohammed/Work/oreilly-books/oreilly_books/download.py` to call a cookie update method after each HTTP request.

