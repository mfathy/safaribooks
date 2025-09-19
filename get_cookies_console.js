// Safari Books Online Cookie Extractor
// Copy and paste this into your browser's console (F12 → Console tab)
// while logged into https://learning.oreilly.com

function extractCookies() {
    console.log("🍪 Safari Books Online Cookie Extractor");
    console.log("=" * 50);
    
    // Get all cookies for the current domain
    const cookies = document.cookie.split(';').reduce((acc, cookie) => {
        const [name, value] = cookie.trim().split('=');
        if (name && value) {
            acc[name] = value;
        }
        return acc;
    }, {});
    
    console.log("Found cookies:");
    Object.entries(cookies).forEach(([name, value]) => {
        console.log(`  ${name}: ${value}`);
    });
    
    // Create JSON format
    const jsonCookies = JSON.stringify(cookies, null, 2);
    console.log("\n📋 JSON format (copy this to cookies.json):");
    console.log(jsonCookies);
    
    // Copy to clipboard if possible
    if (navigator.clipboard) {
        navigator.clipboard.writeText(jsonCookies).then(() => {
            console.log("\n✅ Cookies copied to clipboard!");
            console.log("Now paste the content into cookies.json file");
        }).catch(err => {
            console.log("\n❌ Could not copy to clipboard:", err);
        });
    }
    
    return cookies;
}

// Run the extractor
extractCookies();
