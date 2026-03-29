'use strict';

const LOG_PREFIX = '[bookQueue popup]';

const fileInput = document.getElementById('file');
const fileLabel = document.getElementById('file-label');
const statusEl = document.getElementById('status');
const startBtn = document.getElementById('start');
const pauseBtn = document.getElementById('pause');
const resetBtn = document.getElementById('reset');

/**
 * @param {unknown} raw
 */
function parseQueueItems(raw) {
  if (!Array.isArray(raw)) {
    throw new Error('JSON root must be an array');
  }
  const out = [];
  for (let i = 0; i < raw.length; i++) {
    const row = raw[i];
    if (!row || typeof row !== 'object') continue;
    const o = /** @type {Record<string, unknown>} */ (row);
    const urlRaw = o.url;
    if (typeof urlRaw !== 'string') continue;
    let url;
    try {
      const u = new URL(urlRaw.trim());
      if (u.protocol !== 'http:' && u.protocol !== 'https:') continue;
      u.hash = '';
      url = u.href;
    } catch {
      continue;
    }
    const title =
      typeof o.title === 'string'
        ? o.title
        : o.title != null
          ? String(o.title)
          : '';
    const { url: _u, title: _t, ...metadata } = o;
    out.push({ url, title, metadata });
  }
  return out;
}

async function refreshStatus() {
  try {
    const s = await chrome.runtime.sendMessage({ action: 'getStatus' });
    if (!s) {
      statusEl.textContent = '(no state)';
      return;
    }
    const q = s.queue;
    const n = Array.isArray(q) ? q.length : 0;
    const i = typeof s.index === 'number' ? s.index : 0;
    const lines = [
      `runState: ${s.runState ?? '—'}`,
      `progress: ${n ? `${i + 1} / ${n}` : '0 / 0'}`,
      `workerTabId: ${s.workerTabId ?? '—'}`,
      `lastLog: ${s.lastLog ?? '—'}`,
      `lastError: ${s.lastError ?? '—'}`,
    ];
    statusEl.textContent = lines.join('\n');
  } catch (e) {
    console.error(LOG_PREFIX, 'refreshStatus', e);
    statusEl.textContent = 'Status error: ' + (e instanceof Error ? e.message : String(e));
  }
}

fileInput?.addEventListener('change', async () => {
  fileLabel.textContent = '';
  const file = fileInput.files && fileInput.files[0];
  if (!file) return;

  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    const items = parseQueueItems(parsed);
    if (!items.length) {
      fileLabel.textContent = 'No valid http(s) URLs found.';
      return;
    }
    await chrome.storage.local.set({
      queue: items,
      index: 0,
      runState: 'idle',
      workerTabId: null,
      lastLog: `Loaded ${items.length} item(s).`,
      lastError: '',
    });
    fileLabel.textContent = `${file.name} — ${items.length} item(s)`;
    await refreshStatus();
  } catch (e) {
    console.error(LOG_PREFIX, 'load JSON', e);
    fileLabel.textContent = 'Error: ' + (e instanceof Error ? e.message : String(e));
  }
});

startBtn?.addEventListener('click', async () => {
  try {
    const r = await chrome.runtime.sendMessage({ action: 'start' });
    if (r && r.ok === false) {
      console.error(LOG_PREFIX, 'start', r.error || 'Start failed');
      statusEl.textContent = r.error || 'Start failed';
    }
  } catch (e) {
    console.error(LOG_PREFIX, 'start', e);
    statusEl.textContent = e instanceof Error ? e.message : String(e);
  }
  await refreshStatus();
});

pauseBtn?.addEventListener('click', async () => {
  await chrome.runtime.sendMessage({ action: 'pause' });
  await refreshStatus();
});

resetBtn?.addEventListener('click', async () => {
  try {
    const r = await chrome.runtime.sendMessage({ action: 'reset' });
    if (r && r.ok === false) {
      console.error(LOG_PREFIX, 'reset', r.error || 'Reset failed');
      statusEl.textContent = r.error || 'Reset failed';
    }
  } catch (e) {
    console.error(LOG_PREFIX, 'reset', e);
    statusEl.textContent = e instanceof Error ? e.message : String(e);
  }
  await refreshStatus();
});

console.info(
  LOG_PREFIX,
  'Popup loaded. Logs here only when this popup is inspected (right‑click → Inspect). ' +
    'Main queue logs: chrome://extensions → Service worker → Inspect.'
);

refreshStatus();
setInterval(refreshStatus, 2000);
