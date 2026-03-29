'use strict';

const LOG_PREFIX = '[bookQueue]';

/**
 * @param {string} context
 * @param {unknown} err
 */
function logError(context, err) {
  console.error(LOG_PREFIX, context, err);
}

/**
 * @param {string} context
 * @param {unknown} [detail]
 */
function logWarn(context, detail) {
  if (detail !== undefined) console.warn(LOG_PREFIX, context, detail);
  else console.warn(LOG_PREFIX, context);
}

/**
 * Info-level logs (success path). Errors alone are easy to miss — open the service worker console.
 * @param {string} context
 * @param {unknown} [detail]
 */
function logInfo(context, detail) {
  if (detail !== undefined) console.log(LOG_PREFIX, context, detail);
  else console.log(LOG_PREFIX, context);
}

/**
 * Safe subset of `chrome.tabs.Tab` for logs (no favIconUrl / large fields).
 * @param {chrome.tabs.Tab | undefined | null} tab
 * @returns {Record<string, unknown> | null}
 */
function tabSnapshot(tab) {
  if (!tab || tab.id == null) return null;
  return {
    id: tab.id,
    status: tab.status,
    url: tab.url,
    pendingUrl: tab.pendingUrl,
    title: tab.title,
    active: tab.active,
    discarded: tab.discarded,
  };
}

/**
 * @param {string} context
 * @param {number} tabId
 */
async function logTabState(context, tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    logInfo(context, tabSnapshot(tab));
  } catch (e) {
    logWarn(context + ' (tabs.get failed)', e);
  }
}

logInfo(
  'Service worker started.',
  'Open logs here: chrome://extensions → find this extension → Service worker → Inspect. ' +
    'The learning.oreilly.com tab Console will NOT show these messages.'
);

/** @type {number|null} */
let workerTabId = null;
/** Avoid overlapping inject runs */
let injectChain = Promise.resolve();
/** Skip duplicate tab "complete" while a step is in progress */
let injectInFlight = false;

chrome.storage.local.get('workerTabId').then((s) => {
  if (typeof s.workerTabId === 'number') workerTabId = s.workerTabId;
});

const CONFIG = {
  CLICK_SELECTOR: '#mod_id',
  DONE_TEXT: 'ePub download complete!',
  POST_LOAD_WAIT_MS: 1500,
  SELECTOR_TIMEOUT_MS: 120000,
  DONE_TIMEOUT_MS: 600000,
  POLL_MS: 300,
};

/**
 * @param {string} href
 * @returns {string}
 */
function normalizeUrl(href) {
  try {
    const u = new URL(href);
    u.hash = '';
    return u.href;
  } catch {
    return '';
  }
}

/**
 * O'Reilly Learning often redirects `.../library/view/-/978…/` to
 * `.../library/view/<slug>/978…/`. Same book ID (ISBN-13 in path) = same resource.
 * @param {string} href
 * @returns {string|null}
 */
function extractOReillyBookId(href) {
  try {
    const u = new URL(href);
    if (u.hostname !== 'learning.oreilly.com') return null;
    const m = u.pathname.match(/\/(978\d{10})(?:\/|$)/);
    return m ? m[1] : null;
  } catch {
    return null;
  }
}

/**
 * @param {string} a
 * @param {string} b
 */
function urlsMatch(a, b) {
  if (normalizeUrl(a) === normalizeUrl(b)) return true;
  const ida = extractOReillyBookId(a);
  const idb = extractOReillyBookId(b);
  return ida != null && ida === idb;
}

async function loadState() {
  const data = await chrome.storage.local.get([
    'queue',
    'index',
    'runState',
    'workerTabId',
    'lastLog',
    'lastError',
  ]);
  return data;
}

async function finishQueue() {
  logInfo('Queue finished (all items done or empty).');
  await chrome.storage.local.set({
    runState: 'idle',
    lastLog: 'Queue finished.',
    lastError: '',
    workerTabId: null,
  });
  workerTabId = null;
}

async function navigateToCurrent() {
  const { queue, index } = await loadState();
  if (!queue || !queue.length || index == null || index >= queue.length) {
    await finishQueue();
    return;
  }

  const item = queue[index];
  const url = item.url;

  if (workerTabId == null) {
    const stored = await chrome.storage.local.get('workerTabId');
    if (stored.workerTabId != null) {
      try {
        await chrome.tabs.get(stored.workerTabId);
        workerTabId = stored.workerTabId;
      } catch {
        workerTabId = null;
      }
    }
  }

  if (workerTabId == null) {
    logInfo('Creating tab for queue item', {
      index: index + 1,
      total: queue.length,
      title: item.title || '',
      url,
    });
    const tab = await chrome.tabs.create({ url, active: true });
    workerTabId = tab.id;
    logInfo('Tab created', tabSnapshot(tab));
    await chrome.storage.local.set({ workerTabId });
    await chrome.storage.local.set({
      lastLog: `Navigating [${index + 1}/${queue.length}] ${item.title || url}`,
    });
    return;
  }

  try {
    logInfo('Updating worker tab', { tabId: workerTabId, url });
    await chrome.tabs.update(workerTabId, { url, active: true });
    await logTabState('Tab state after tabs.update', workerTabId);
    await chrome.storage.local.set({
      lastLog: `Navigating [${index + 1}/${queue.length}] ${item.title || url}`,
    });
  } catch (e) {
    logWarn('tabs.update failed; creating new tab', e);
    const tab = await chrome.tabs.create({ url, active: true });
    workerTabId = tab.id;
    logInfo('Tab created (fallback)', tabSnapshot(tab));
    await chrome.storage.local.set({ workerTabId });
  }
}

/**
 * @param {number} tabId
 */
async function runInject(tabId) {
  const state = await loadState();
  if (state.runState !== 'running') return;

  const { queue, index } = state;
  if (!queue || index == null || index >= queue.length) return;

  const item = queue[index];
  const tab = await chrome.tabs.get(tabId).catch(() => null);
  logInfo('runInject: tab state', tabSnapshot(tab));
  if (!tab?.url || !urlsMatch(tab.url, item.url)) {
    const detail = { expected: item.url, actual: tab?.url ?? null, index };
    logError('runInject: tab URL mismatch', detail);
    await chrome.storage.local.set({
      lastLog: 'Tab URL mismatch; expected current queue URL.',
      lastError: 'Tab URL mismatch',
    });
    return;
  }

  await chrome.storage.local.set({
    lastLog: `Waiting for UI & download [${index + 1}/${queue.length}]…`,
  });

  logInfo('runInject: waiting for selector + completion text', {
    tabId,
    index: index + 1,
    total: queue.length,
    title: item.title || '',
    clickSelector: CONFIG.CLICK_SELECTOR,
    doneText: CONFIG.DONE_TEXT,
  });

  const injectConfig = {
    clickSelector: CONFIG.CLICK_SELECTOR,
    doneSubstr: CONFIG.DONE_TEXT,
    postLoadWaitMs: CONFIG.POST_LOAD_WAIT_MS,
    selectorTimeoutMs: CONFIG.SELECTOR_TIMEOUT_MS,
    doneTimeoutMs: CONFIG.DONE_TIMEOUT_MS,
    pollMs: CONFIG.POLL_MS,
  };

  let results;
  try {
    results = await chrome.scripting.executeScript({
      target: { tabId, allFrames: false },
      func: async (cfg) => {
        /**
         * @param {string} selector
         * @param {number} timeoutMs
         * @param {number} intervalMs
         */
        function waitForSelector(selector, timeoutMs, intervalMs) {
          const deadline = Date.now() + timeoutMs;
          return new Promise((resolve, reject) => {
            const tick = () => {
              const el = document.querySelector(selector);
              if (el) {
                resolve(/** @type {HTMLElement} */ (el));
                return;
              }
              if (Date.now() > deadline) {
                reject(new Error('Timeout waiting for selector: ' + selector));
                return;
              }
              setTimeout(tick, intervalMs);
            };
            tick();
          });
        }

        /**
         * @param {string} substr
         * @param {number} timeoutMs
         * @param {number} intervalMs
         */
        function waitForTextInDiv(substr, timeoutMs, intervalMs) {
          const deadline = Date.now() + timeoutMs;
          const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
          const needle = norm(substr);
          return new Promise((resolve, reject) => {
            const tick = () => {
              const divs = document.getElementsByTagName('div');
              for (let i = 0; i < divs.length; i++) {
                if (norm(divs[i].textContent).includes(needle)) {
                  resolve(true);
                  return;
                }
              }
              if (Date.now() > deadline) {
                reject(new Error('Timeout waiting for text: ' + substr));
                return;
              }
              setTimeout(tick, intervalMs);
            };
            tick();
          });
        }

        try {
          await new Promise((r) => setTimeout(r, cfg.postLoadWaitMs));
          const el = await waitForSelector(
            cfg.clickSelector,
            cfg.selectorTimeoutMs,
            cfg.pollMs
          );
          el.click();
          await waitForTextInDiv(cfg.doneSubstr, cfg.doneTimeoutMs, cfg.pollMs);
          return { ok: true };
        } catch (e) {
          return { ok: false, error: e instanceof Error ? e.message : String(e) };
        }
      },
      args: [injectConfig],
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    logError('executeScript', e);
    await chrome.storage.local.set({
      runState: 'error',
      lastError: msg,
      lastLog: 'Inject failed: ' + msg,
    });
    return;
  }

  const first = results && results[0];
  const result = first && first.result;

  if (result && result.ok) {
    const nextIndex = index + 1;
    logInfo('Step OK (clicked + saw completion text)', {
      completed: index + 1,
      total: queue.length,
      nextIndex: nextIndex + 1,
    });
    await chrome.storage.local.set({
      index: nextIndex,
      lastError: '',
      lastLog: `Done [${index + 1}/${queue.length}]. Next…`,
    });

    if (nextIndex >= queue.length) {
      await finishQueue();
      return;
    }

    await navigateToCurrent();
    return;
  }

  const err = (result && result.error) || 'Unknown inject error';
  logError('inject step failed', err);
  await chrome.storage.local.set({
    runState: 'error',
    lastError: err,
    lastLog: 'Step failed: ' + err,
  });
}

function chainErrorHandler(e) {
  injectInFlight = false;
  const msg = e instanceof Error ? e.message : String(e);
  logError('inject chain', e);
  return chrome.storage.local.set({
    runState: 'error',
    lastError: msg,
    lastLog: 'Chain error: ' + msg,
  });
}

/**
 * Serialized queue: one inject at a time.
 * @param {number} tabId
 * @param {{ skipUrlCheck?: boolean }} [opts]
 */
function enqueueInject(tabId, opts) {
  const skipUrlCheck = opts && opts.skipUrlCheck === true;
  injectChain = injectChain
    .then(async () => {
      if (injectInFlight) return;

      const st = await loadState();
      if (st.runState !== 'running') return;
      if (st.workerTabId == null || tabId !== st.workerTabId) return;

      const { queue, index } = st;
      if (!queue || index == null || index >= queue.length) return;

      if (!skipUrlCheck) {
        const tab = await chrome.tabs.get(tabId).catch(() => null);
        logInfo('enqueueInject: tab state before URL check', tabSnapshot(tab));
        if (!tab?.url) return;
        if (!urlsMatch(tab.url, queue[index].url)) {
          logInfo('enqueueInject: skip (URL does not match queue item)', {
            tabUrl: tab.url,
            expected: queue[index].url,
            index: index + 1,
          });
          return;
        }
      }

      injectInFlight = true;
      try {
        logInfo('enqueueInject: running', { tabId, skipUrlCheck });
        await runInject(tabId);
      } finally {
        injectInFlight = false;
      }
    })
    .catch(chainErrorHandler);
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status !== 'complete') return;
  logInfo('tabs.onUpdated: complete', {
    tabId,
    changeInfo,
    tabFromEvent: tabSnapshot(tab),
  });
  void logTabState('tabs.onUpdated: complete (tabs.get)', tabId);
  enqueueInject(tabId);
});

chrome.tabs.onRemoved.addListener(async (tabId) => {
  const { workerTabId: stored } = await chrome.storage.local.get('workerTabId');
  if (tabId === workerTabId || tabId === stored) {
    logInfo('Worker tab closed', { tabId, hadWorker: true });
    workerTabId = null;
    await chrome.storage.local.set({ workerTabId: null });
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.action === 'start') {
    startOrResume()
      .then(() => sendResponse({ ok: true }))
      .catch((e) => {
        logError('startOrResume', e);
        sendResponse({ ok: false, error: e instanceof Error ? e.message : String(e) });
      });
    return true;
  }
  if (msg?.action === 'pause') {
    logInfo('Pause requested');
    chrome.storage.local
      .set({ runState: 'paused', lastLog: 'Paused.' })
      .then(() => sendResponse({ ok: true }));
    return true;
  }
  if (msg?.action === 'reset') {
    resetQueue()
      .then(() => sendResponse({ ok: true }))
      .catch((e) => {
        logError('resetQueue', e);
        sendResponse({ ok: false, error: e instanceof Error ? e.message : String(e) });
      });
    return true;
  }
  if (msg?.action === 'getStatus') {
    loadState().then((s) => sendResponse(s));
    return true;
  }
  return false;
});

async function resetQueue() {
  logInfo('Reset: clearing queue state');
  workerTabId = null;
  injectChain = Promise.resolve();
  await chrome.storage.local.remove([
    'queue',
    'index',
    'runState',
    'workerTabId',
    'lastLog',
    'lastError',
  ]);
}

async function startOrResume() {
  logInfo('startOrResume');
  const state = await loadState();
  const { queue, index } = state;
  if (!queue?.length) {
    logWarn('No queue in storage — load JSON in the popup first');
    await chrome.storage.local.set({ lastLog: 'No queue. Load a JSON file first.' });
    return;
  }
  if (index == null || index < 0) {
    await chrome.storage.local.set({ index: 0 });
  }

  await chrome.storage.local.set({ runState: 'running', lastError: '' });

  const idx = (await loadState()).index ?? 0;
  const q = (await loadState()).queue;
  if (!q || idx >= q.length) {
    await finishQueue();
    return;
  }

  const current = q[idx];
  const stored = await chrome.storage.local.get('workerTabId');
  let tabId = stored.workerTabId ?? null;
  if (tabId != null) {
    try {
      const tab = await chrome.tabs.get(tabId);
      workerTabId = tab.id;
      if (tab.url && urlsMatch(tab.url, current.url)) {
        logInfo('Resume: tab already on current URL; enqueue inject', {
          tab: tabSnapshot(tab),
          expectedUrl: current.url,
        });
        enqueueInject(tab.id, { skipUrlCheck: true });
        return;
      }
    } catch (e) {
      logWarn('tabs.get(workerTabId)', e);
      workerTabId = null;
      tabId = null;
    }
  }

  await navigateToCurrent();
}

chrome.runtime.onStartup.addListener(() => {
  workerTabId = null;
});

chrome.runtime.onInstalled.addListener((details) => {
  workerTabId = null;
  logInfo('onInstalled', { reason: details.reason, previousVersion: details.previousVersion });
});
