'use strict';
/*
 * Repeatable browser acceptance for the owner-private dashboard.
 *
 * It uses the production launcher and the real one-time sign-in flow: the nonce and the session cookie
 * stay in process memory, are never printed, never written to disk and never committed. Playwright is
 * intentionally NOT a repository dependency; run it with NODE_PATH pointing at an installed copy:
 *
 *   set NODE_PATH=C:\path\to\node_modules
 *   node dashboard/e2e/browser_acceptance.cjs
 *
 * Environment overrides: ACASH_ROOT, ACASH_UV, ACASH_CHROME, ACASH_DASHBOARD.
 * Exit code 0 = every check passed, 1 = at least one check failed or the run could not start.
 */
const { spawn } = require('child_process');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = process.env.ACASH_ROOT || path.resolve(__dirname, '..', '..');
const UV = process.env.ACASH_UV || 'uv';
const CHROME = process.env.ACASH_CHROME || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DASHBOARD = process.env.ACASH_DASHBOARD || 'http://127.0.0.1:3002/';
const API = 'http://127.0.0.1:8765/api/upi';
const MARKET = 'http://127.0.0.1:8765/api/upi/market';
const TIMEOUT_MS = 90000;

const checks = [];
const sanitize = (text) => String(text).replace(/nonce=[A-Za-z0-9_-]+/g, 'nonce=REDACTED');
const record = (name, ok, detail) => { checks.push({ name, ok: Boolean(ok), detail }); };
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

let launcher;
let browser;

async function api(page, route, base = API) {
  return page.evaluate(async (url) => {
    try {
      const response = await fetch(url, { credentials: 'include', cache: 'no-store' });
      const body = await response.json().catch(() => ({}));
      return { http: response.status, body };
    } catch (error) {
      return { http: 0, body: { error: String(error).slice(0, 120) } };
    }
  }, `${base}/${route}`);
}

async function main() {
  let buffer = '';
  let settle;
  let fail;
  const signIn = new Promise((resolve, reject) => { settle = resolve; fail = reject; });

  browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  launcher = spawn(UV, ['run', '--quiet', 'python', '-m', 'acash.dashboard_api.launcher', '--no-browser'],
    { cwd: ROOT, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  let errText = '';
  launcher.stderr.on('data', (chunk) => {
    errText = sanitize((errText + chunk.toString()).slice(-1200));
  });
  launcher.stdout.on('data', (chunk) => {
    buffer += chunk.toString();
    const found = buffer.match(/http:\/\/127\.0\.0\.1:\d+\/api\/upi\/session\?nonce=[A-Za-z0-9_-]+/);
    if (found) { settle(found[0]); buffer = ''; }
    if (buffer.length > 40000) buffer = buffer.slice(-8000);
  });
  launcher.on('error', (error) => fail(new Error(`launcher spawn failed: ${error.code || error.message}`)));
  launcher.on('exit', (code) => fail(new Error(`launcher exited ${code}${errText ? ': ' + errText : ''}`)));

  const url = await Promise.race([signIn, sleep(TIMEOUT_MS).then(() => { throw new Error('sign-in not issued'); })]);
  try {
    await page.goto(url, { waitUntil: 'commit', timeout: 45000 });
  } catch (error) {
    // One retry: a freshly started service can accept the connection before the dashboard is ready.
    await sleep(3000);
    await page.goto(url, { waitUntil: 'commit', timeout: 45000 });
  }
  await page.waitForTimeout(3000);
  record('sign-in redirects to the dashboard', !page.url().includes('/api/upi/session'), page.url().split('?')[0]);

  const view = await api(page, 'view');
  record('private API authenticated', view.http === 200, `HTTP ${view.http}`);
  record('28 position rows', (view.body.positions?.rows ?? []).length === 28,
    `${(view.body.positions?.rows ?? []).length} rows`);
  record('owner-private mode (no synthetic fallback)',
    view.body.data_mode === 'OWNER_PRIVATE_READ_ONLY', view.body.data_mode);

  const rows = view.body.positions?.rows ?? [];
  const bySymbol = Object.fromEntries(rows.map((row) => [row.security_id, row]));
  record('HOOD has a qualified value', Number(bySymbol.HOOD?.value_local) > 0, bySymbol.HOOD?.value_local);
  record('GE and GEV are distinct', Boolean(bySymbol.GE) && Boolean(bySymbol.GEV) && bySymbol.GE.figi !== bySymbol.GEV.figi,
    `${bySymbol.GE?.figi} / ${bySymbol.GEV?.figi}`);

  const research = await api(page, 'research', MARKET);
  const cohorts = research.body.cohorts ?? [];
  record('research cohorts present', research.http === 200 && cohorts.length === 2, `HTTP ${research.http} · ${cohorts.length} cohorts`);
  const recent = cohorts.find((c) => c.cohort_id === 'RECENT_INCEPTION');
  record('recent-inception cohort is not comparable',
    recent && recent.comparable_to_established === false, recent?.evaluation_status);

  const session = await api(page, 'session', MARKET);
  record('market session is venue verified', session.body.calendar_status === 'VERIFIED_VENUE_FIXTURE',
    session.body.mic);
  record('Bangkok open time present', Boolean(session.body.today?.open_ict), session.body.today?.open_ict);

  const tax = await api(page, 'tax');
  record('tax evidence available', tax.http === 200 && tax.body.status === 'AVAILABLE', tax.body.status);
  record('tax liability stays unestablished', tax.body.tax_liability?.status === 'NOT_ESTABLISHED',
    tax.body.tax_liability?.status);

  // Holdings UI
  const holdingsTab = page.getByRole('tab', { name: 'พอร์ตของฉัน' });
  await holdingsTab.click();
  await page.waitForTimeout(500);
  const detailButtons = page.locator('button[aria-label^="รายละเอียด"]');
  record('holdings table renders every row', (await detailButtons.count()) === 28, `${await detailButtons.count()}`);

  const search = page.locator('input[placeholder*="ค้นหา"]');
  await search.fill('HOOD');
  await page.waitForTimeout(300);
  record('holdings search narrows to HOOD', (await detailButtons.count()) === 1, `${await detailButtons.count()}`);

  await search.fill('');
  await page.waitForTimeout(300);
  const valueHeader = page.getByRole('button', { name: 'มูลค่า' }).first();
  await valueHeader.click();
  record('holdings sorting toggles', (await valueHeader.getAttribute('aria-pressed')) === 'true',
    await valueHeader.getAttribute('aria-pressed'));

  const orderButtons = await page.locator('button').evaluateAll((buttons) =>
    buttons.map((b) => (b.textContent || '').replace(/\s+/g, ' ').trim())
      .filter((text) => /^(ซื้อ|ขาย|ซื้อขาย|buy|sell)$/i.test(text)));
  record('no order control', orderButtons.length === 0, JSON.stringify(orderButtons));

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(300);
  const narrow = await page.evaluate(() => {
    const width = window.innerWidth;
    const culprits = Array.from(document.querySelectorAll('body *'))
      .map((el) => ({ el, rect: el.getBoundingClientRect() }))
      .filter(({ rect }) => rect.right > width + 1)
      .sort((a, b) => b.rect.right - a.rect.right)
      .slice(0, 4)
      .map(({ el, rect }) => `${el.tagName.toLowerCase()}.${String(el.className || '').split(' ').slice(0, 3).join('.')}`
        + ` right=${Math.round(rect.right)}`);
    return { overflow: document.documentElement.scrollWidth - width, culprits };
  });
  record('narrow viewport stays usable', narrow.overflow <= 8,
    `overflow ${narrow.overflow}px · ${narrow.culprits.join(' | ')}`);

  // Authenticated reload
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
  const reload = await api(page, 'view');
  record('reload keeps the session', reload.http === 200, `HTTP ${reload.http}`);

  // A fresh context has no cookie.
  const other = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const anon = await other.newPage();
  await anon.goto(DASHBOARD, { waitUntil: 'domcontentloaded' }).catch(() => {});
  const unauth = await api(anon, 'view');
  record('fresh browser is rejected', unauth.http === 401, `HTTP ${unauth.http}`);
  await other.close();

  await context.close();
}

main()
  .catch((error) => record('harness completed', false, sanitize(error.message).slice(0, 240)))
  .finally(async () => {
    if (browser) { try { await browser.close(); } catch (_) { /* ignore */ } }
    if (launcher && !launcher.killed) {
      const kill = spawn('taskkill', ['/T', '/F', '/PID', String(launcher.pid)], { windowsHide: true, stdio: 'ignore' });
      await new Promise((resolve) => { kill.on('exit', resolve); setTimeout(resolve, 3000); });
    }
    const failed = checks.filter((check) => !check.ok);
    console.log(JSON.stringify({
      result: failed.length === 0 ? 'BROWSER_E2E_PASS' : 'BROWSER_E2E_FAIL',
      outputSanitized: true,
      passed: checks.length - failed.length,
      failed: failed.length,
      checks,
      nonceExposedInOutput: false,
      sessionMaterialPersisted: false,
    }, null, 2));
    process.exitCode = failed.length === 0 ? 0 : 1;
  });
