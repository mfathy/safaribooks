# Book Queue extension (POC)

Serial automation for `https://learning.oreilly.com/*`: loads a JSON array (`url`, `title`, …), opens each URL in a dedicated tab, waits for `#mod_id` (“Get ebook”), clicks it, then waits for the text `ePub download complete!` before moving on.

## Load unpacked (Chrome)

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. **Load unpacked** → select this `extension` folder.

## Use

1. Sign in to O’Reilly in Chrome (same profile as the extension).
2. Click the extension icon → **Choose JSON** (e.g. `oreilly-books-2026-01-25.json`).
3. **Start**. A tab navigates per item; progress appears in the popup status area.
4. **Pause** / **Reset** as needed.

## Configure selectors / timing

Edit constants at the top of `background.js`:

- `CLICK_SELECTOR` — default `#mod_id`
- `DONE_TEXT` — default `ePub download complete!`
- `POST_LOAD_WAIT_MS`, `SELECTOR_TIMEOUT_MS`, `DONE_TIMEOUT_MS`, `POLL_MS`

## Console logs

Extension code does **not** print to the **learning.oreilly.com** tab’s DevTools Console. If you look there, you will see nothing from this extension.

- **Background (main queue logs):** `chrome://extensions` → find **O'Reilly Book Queue (POC)** → **Service worker** → **Inspect**. You should see `[bookQueue]` lines (`console.log` / `console.warn` / `console.error`) when you load the extension, click **Start**, navigate, etc.
- **Popup:** Open the extension popup → right‑click inside it → **Inspect** → Console. Look for `[bookQueue popup]`.

After editing code, click **Reload** on the extension card, then open **Service worker → Inspect** again so the worker restarts and logs the startup line.

## Notes

- Host access is limited to `https://learning.oreilly.com/*` in `manifest.json`; extend `host_permissions` if your queue uses other origins.
- The service worker may sleep; `workerTabId` is stored so tab matching still works after wake.
- Respect O’Reilly’s terms of use; this POC is for testing with your own account.
