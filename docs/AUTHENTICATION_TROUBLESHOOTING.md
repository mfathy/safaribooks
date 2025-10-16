# 🔐 Authentication Troubleshooting Guide

## 🐛 Problem: Access Denied (403 Error)

You're getting:
```
Authentication issue: unable to access profile page.
403 Access Denied
You don't have permission to access "http://learning.oreilly.com/profile/"
```

## 🔍 Common Causes

### 1. **Expired Cookies** (Most Common)
O'Reilly cookies expire after a period of inactivity or after a set time.

### 2. **Rate Limiting / Bot Detection**
Downloading many books quickly can trigger O'Reilly's bot detection:
- Too many requests in short time
- Unusual access patterns
- Multiple concurrent downloads

### 3. **Session Invalidation**
- Logged in from another browser/device
- Changed password
- Security settings changed
- IP address changed (VPN, etc.)

### 4. **Account Issues**
- Subscription expired
- Account suspended
- Terms of service violation

## ✅ Solutions

### Solution 1: Refresh Your Cookies (Recommended)

**Step 1: Clear Old Cookies**
```bash
# Backup old cookies
cp cookies.json cookies_backup.json

# Or delete them
rm cookies.json
```

**Step 2: Get Fresh Cookies**

Follow the instructions in `COOKIE_SETUP.md`:

1. **Open Browser** (Chrome/Firefox)
2. **Log into O'Reilly**: https://learning.oreilly.com/
3. **Open Developer Tools**: F12 or Right-click → Inspect
4. **Go to Application/Storage Tab**
5. **Find Cookies** for `learning.oreilly.com`
6. **Export Important Cookies**:
   - `orm-jwt`
   - `BrowserCookie`
   - `csrftoken`
   - Any other O'Reilly-specific cookies

7. **Create `cookies.json`**:
```json
{
  "orm-jwt": "your_jwt_token_here",
  "BrowserCookie": "your_browser_cookie_here",
  "csrftoken": "your_csrf_token_here"
}
```

**Step 3: Test Authentication**
```bash
# Test with a single book
python3 oreilly_books.py 9781098125967
```

### Solution 2: Slow Down Downloads

If rate limited, reduce download speed:

**Update `download_config.json`:**
```json
{
  "download_delay": 10,
  "max_workers": 1,
  "max_books_per_skill": 5
}
```

**Wait Before Retrying:**
```bash
# Wait 30-60 minutes before trying again
# O'Reilly's rate limits usually reset after some time
```

### Solution 3: Use Conservative Settings

**For Large Downloads:**
```json
{
  "download_delay": 15,
  "max_workers": 1,
  "max_books_per_skill": 10,
  "max_pages_per_skill": 3
}
```

**Download in Smaller Batches:**
```bash
# Download one skill at a time
python3 download_books.py --skills "Python" --max-books 5

# Wait 10-15 minutes between skills
```

### Solution 4: Check Your Account

1. **Verify Subscription**: Log into https://learning.oreilly.com/
2. **Check Account Status**: Make sure it's active
3. **Review Activity**: Check if there are any warnings

### Solution 5: Change User Agent

Sometimes using a different user agent helps:

**Edit `oreilly_books/auth.py`** (if it exists) or the session headers to use:
```python
'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
```

### Solution 6: Use VPN or Different Network

If your IP is temporarily blocked:
- Try from a different network
- Use a VPN (if allowed by your organization)
- Wait a few hours and try again

## 🎯 Recommended Approach

### Immediate Fix:

1. **Refresh cookies** (most likely to work)
   ```bash
   # Backup old cookies
   cp cookies.json cookies_backup.json
   
   # Get fresh cookies from browser (see COOKIE_SETUP.md)
   # Save to cookies.json
   ```

2. **Test with single book**
   ```bash
   python3 oreilly_books.py 9781098125967
   ```

3. **If successful, resume downloads with conservative settings**
   ```bash
   python3 download_books.py --max-books 5 --workers 1
   ```

### Long-term Strategy:

1. **Use Conservative Settings**
   - 1 worker at a time
   - 10+ second delays
   - Download in batches

2. **Schedule Downloads**
   - Download during off-peak hours
   - Spread downloads over days/weeks
   - Take breaks between batches

3. **Monitor Progress**
   ```bash
   python3 oreilly_automation.py --progress
   ```

## 🔧 Quick Fixes to Try

### Try 1: Fresh Cookies
```bash
# Get new cookies and test
python3 oreilly_books.py 9781098125967
```

### Try 2: Wait and Retry
```bash
# Wait 30 minutes, then try with slow settings
python3 download_books.py --max-books 3 --workers 1
```

### Try 3: Single Skill Test
```bash
# Test with just one skill
python3 download_books.py --skills "Python" --max-books 2
```

## 📊 Debugging Steps

### 1. Check Cookie Format
```bash
# Verify cookies.json is valid JSON
python3 -m json.tool cookies.json
```

### 2. Check Cookie Age
```bash
# See when cookies were last modified
ls -lh cookies.json
```

### 3. Test Direct Access
```bash
# Try downloading a single book directly
python3 oreilly_books.py 9781098125967
```

### 4. Check Logs
```bash
# Look for more details in logs
tail -50 book_downloader.log
```

## ⚠️ Important Notes

### Rate Limiting
O'Reilly monitors:
- Number of downloads per hour
- Number of API requests
- Download patterns
- Multiple concurrent connections

### Best Practices
1. **Respect Rate Limits**: Don't overwhelm their servers
2. **Use Delays**: 5-10 seconds between downloads
3. **Single Thread**: Use max_workers=1 for large downloads
4. **Batch Processing**: Download in small batches
5. **Off-Peak Hours**: Download during nights/weekends

### Don't Do This
- ❌ Don't use max_workers > 2
- ❌ Don't set download_delay < 3
- ❌ Don't download hundreds of books at once
- ❌ Don't retry immediately after 403 error
- ❌ Don't share cookies between devices

## 🎯 Most Likely Fix

**99% of the time, you just need fresh cookies:**

1. Open browser (where you're logged into O'Reilly)
2. Go to Developer Tools → Application → Cookies
3. Copy `orm-jwt` and other O'Reilly cookies
4. Update `cookies.json`
5. Try again

## 📞 If Nothing Works

1. **Wait 24 hours** - Rate limits usually reset
2. **Contact O'Reilly Support** - If account issue
3. **Check Subscription** - Ensure it's active
4. **Try Different Network** - If IP blocked
5. **Review Terms of Service** - Ensure compliance

## 🔄 Recovery Steps

After getting it working again:

```bash
# 1. Test authentication
python3 oreilly_books.py 9781098125967

# 2. If successful, resume with conservative settings
python3 download_books.py --workers 1 --max-books 5

# 3. Monitor progress
python3 oreilly_automation.py --progress

# 4. Gradually increase if stable
# After 10-20 successful downloads, try:
# python3 download_books.py --workers 2 --max-books 10
```

---

**TL;DR**: Get fresh cookies from your browser, use slower settings (1 worker, 10s delay), and download in smaller batches. 🍪

