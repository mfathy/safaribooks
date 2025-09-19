# 🍪 Cookie Setup Guide

To use the Safari Books downloader, you need to extract authentication cookies from your browser.

## Quick Setup

1. **Log into O'Reilly Learning**
   - Go to: https://learning.oreilly.com/login/
   - Enter your credentials and log in

2. **Navigate to your profile page**
   - Go to: https://learning.oreilly.com/profile/
   - Make sure you can see your profile information

3. **Extract cookies manually**
   - Open Developer Tools (F12)
   - Go to Console tab
   - Copy and paste this code:

```javascript
// Extract cookies
const cookies = document.cookie.split(';').reduce((acc, cookie) => {
    const [name, value] = cookie.trim().split('=');
    if (name && value) acc[name] = value;
    return acc;
}, {});

const jsonCookies = JSON.stringify(cookies, null, 2);
console.log('Copy this to cookies.json:');
console.log(jsonCookies);

// Copy to clipboard if possible
if (navigator.clipboard) {
    navigator.clipboard.writeText(jsonCookies);
    console.log('✅ Cookies copied to clipboard!');
}
```

4. **Save the cookies**
   - Copy the JSON output from the console
   - Save it to `cookies.json` file in this directory
   - Make sure the file contains valid JSON

5. **Test the downloader**
   ```bash
   python3 safaribooks.py 9780136766803
   ```

## Troubleshooting

- **No cookies found**: Make sure you're logged in and on the profile page
- **Invalid cookies**: Try logging out and logging back in
- **Expired cookies**: Extract new cookies when they expire

## Notes

- Cookies expire periodically, so you'll need to extract them again
- You must be on `learning.oreilly.com` domain for cookies to be accessible
- The `cookies.json` file should contain valid JSON with cookie name-value pairs
