import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  classifyResponse,
  classifyView,
  formatDec,
  formatWeight,
  parseUpiView,
  NOT_ESTABLISHED,
  PRIVATE_ENDPOINT,
} from '../src/services/upiView.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf-8');
const fixture = (name) => JSON.parse(read(`src/fixtures/${name}`));
const FULL = 'upi_synthetic_view.json';
const EVIDENCE_ONLY = 'upi_synthetic_evidence_only_view.json';

test('synthetic fixtures validate only in SYNTHETIC_DEMO mode', () => {
  for (const name of [FULL, EVIDENCE_ONLY]) {
    const view = parseUpiView(fixture(name), 'SYNTHETIC_DEMO');
    assert.equal(view.governance.observation_authority.observation_authority, 'NOT_REQUIRED_SYNTHETIC_FIXTURE');
    assert.throws(() => parseUpiView(fixture(name), 'OWNER_PRIVATE_READ_ONLY'), /data_mode/);
  }
});

test('golden values pass through as strings and computed NAV is not total best evidence', () => {
  const ov = parseUpiView(fixture(FULL), 'SYNTHETIC_DEMO').portfolio_overview;
  assert.deepEqual(
    [ov.computed_nav_ppds, ov.observed_position_value, ov.unclassified_holdings_value, ov.total_best_evidence],
    ['77220.00', '8250.00', '10280.00', '85470.00'],
  );
  assert.equal(ov.computed_nav_is_total_best_evidence, false);
  assert.notEqual(ov.computed_nav_ppds, ov.total_best_evidence);
});

test('decimal display never uses floats and unknown is never zero', () => {
  assert.equal(formatDec('95750.00'), '95,750.00');
  assert.equal(formatDec('-1234567.891', 'THB'), '-1,234,567.891 THB');
  assert.equal(formatDec('0.10'), '0.10');
  assert.equal(formatWeight('0.4136'), '41.36%');
  assert.equal(formatWeight('1.0000'), '100.00%');
  assert.equal(formatWeight('0.0005'), '0.05%');
  for (const missing of [null, undefined]) {
    assert.equal(formatDec(missing), NOT_ESTABLISHED);
    assert.equal(formatWeight(missing), NOT_ESTABLISHED);
  }
  assert.equal(formatDec('1e3'), 'INVALID');
});

test('evidence-only view keeps computed allocation null and is a warning state', () => {
  const state = classifyView(fixture(EVIDENCE_ONLY), 'SYNTHETIC_DEMO');
  assert.equal(state.status, 'READY_WITH_WARNINGS');
  assert.equal(state.view.allocation.computed_by_classification, null);
  assert.ok(state.warnings.includes('EVIDENCE_ONLY_REPORT'));
});

const mutations = {
  'amount as number': (v) => { v.portfolio_overview.total_best_evidence = 95750; },
  'missing amount': (v) => { delete v.portfolio_overview.computed_nav_ppds; },
  'computed NAV claimed as total': (v) => { v.portfolio_overview.computed_nav_is_total_best_evidence = true; },
  'unknown schema': (v) => { v.view_schema = 'ACASH_UPI_VIEW_V0'; },
  'orders generated': (v) => { v.decision_status.orders_generated = 1; },
  'trading authority claimed': (v) => { v.governance.observation_authority.trading_authority = 'GRANTED'; },
  'computed allocation on evidence-only': (v) => { v.report_metadata.report_type = 'EVIDENCE_ONLY_REPORT'; },
  'non-decimal account total difference': (v) => { v.accounts[0].account_total.difference = 'about 3'; },
  'float weight': (v) => { v.concentration.top1_weight = 0.4136; },
  'not an object': () => null,
};

for (const [name, mutate] of Object.entries(mutations)) {
  test(`malformed or contradictory view is INVALID_REPORT: ${name}`, () => {
    const view = fixture(FULL);
    const replaced = mutate(view);
    const state = classifyView(replaced === null ? null : view, 'SYNTHETIC_DEMO');
    assert.equal(state.status, 'INVALID_REPORT');
    assert.equal('view' in state, false);
  });
}

test('stale valuation is surfaced as STALE', () => {
  const view = fixture(FULL);
  view.report_metadata.valuation_stale = true;
  assert.equal(classifyView(view, 'SYNTHETIC_DEMO').status, 'STALE');
});

test('private responses map to explicit states and never fall back to synthetic data', () => {
  assert.equal(classifyResponse(401, { status: 'SESSION_TOKEN_REQUIRED' }).status, 'AUTHORIZATION_REQUIRED');
  const revoked = classifyResponse(403, { status: 'AUTHORIZATION_REQUIRED', odr_state: 'REVOKED' });
  assert.deepEqual(revoked, { status: 'AUTHORIZATION_REQUIRED', detail: 'AUTHORIZATION_REQUIRED (REVOKED)' });
  assert.equal(classifyResponse(404, { status: 'NO_REPORT' }).status, 'NO_REPORT');
  assert.equal(classifyResponse(404, { status: 'NOT_FOUND' }).status, 'SERVICE_UNAVAILABLE');
  assert.equal(classifyResponse(422, { status: 'INVALID_REPORT' }).status, 'INVALID_REPORT');
  assert.equal(classifyResponse(503, null).status, 'SERVICE_UNAVAILABLE');
  assert.equal(classifyResponse(200, fixture(FULL)).status, 'INVALID_REPORT');
  const privateView = fixture(FULL);
  privateView.data_mode = 'OWNER_PRIVATE_READ_ONLY';
  privateView.governance.observation_authority.observation_authority = 'OWNER_PRIVATE_READ_ONLY_OBSERVATION';
  assert.equal(classifyResponse(200, privateView).status, 'READY_WITH_WARNINGS');
});

test('repository and page keep private values out of storage, URLs, logs and analytics', () => {
  const sources = ['src/services/upiRepository.ts', 'src/services/upiView.ts', 'src/pages/PortfolioPage.tsx'].map(read).join('\n');
  for (const banned of [/localStorage/, /sessionStorage/, /document\.cookie/, /URLSearchParams/, /console\./,
    /import\.meta\.env/, /gtag|analytics|sendBeacon/i, /method:\s*'(POST|PUT|PATCH|DELETE)'/, /mockData|shadowMockData/]) {
    assert.doesNotMatch(sources, banned, `banned pattern ${banned}`);
  }
  assert.equal(PRIVATE_ENDPOINT, 'http://127.0.0.1:8765/api/upi/view');
  assert.match(read('src/services/upiRepository.ts'), /cache:\s*'no-store'/);
  const repo = read('src/services/upiRepository.ts');
  assert.match(repo, /credentials:\s*'include'/);
  assert.doesNotMatch(repo, /credentials:\s*'omit'|TOKEN_HEADER/);
});

test('portfolio opens signed in from the launcher without any token entry', () => {
  assert.match(read('src/components/layout/CommandPalette.tsx'), /id: 'portfolio' as DashboardTab/);
  const app = read('src/App.tsx');
  assert.match(app, /function initialTab\(\)/);
  assert.match(app, /: 'portfolio';/);
  assert.match(app, /RESEARCH_TABS/);
  const page = read('src/pages/PortfolioPage.tsx');
  assert.doesNotMatch(page, /type="password"|Session token|setToken/);
  assert.match(page, /upiRepository\.callInput\('GET', 'status'\)/);
});

test('golden figures are not hardcoded in the UI', () => {
  const page = read('src/pages/PortfolioPage.tsx');
  for (const figure of ['77220', '77,220', '95750', '95,750', '10280', '8250']) {
    assert.equal(page.includes(figure), false, figure);
  }
});

test('no wealth pack or view data in public assets or the build output', () => {
  for (const dir of ['public', 'dist']) {
    const abs = path.join(root, dir);
    if (!fs.existsSync(abs)) continue;
    const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) =>
      e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);
    for (const file of walk(abs)) {
      assert.doesNotMatch(path.basename(file), /upi_|wealth|snapshot|manifest\.json$/i, file);
      if (/\.(js|json|html)$/.test(file)) {
        assert.equal(fs.readFileSync(file, 'utf-8').includes('"data_mode": "OWNER_PRIVATE_READ_ONLY"'), false, file);
      }
    }
  }
});

test('nginx CSP allows only same-origin connections and keeps the shadow proxy', () => {
  const conf = read('nginx.conf');
  const csps = [...conf.matchAll(/Content-Security-Policy "([^"]+)"/g)].map((m) => m[1]);
  assert.equal(csps.length, 2, 'server-level CSP and the static-asset location repeat');
  assert.equal(csps[0], csps[1]);
  const assets = conf.slice(conf.indexOf('location ~*'));
  for (const header of ['X-Content-Type-Options', 'X-Frame-Options', 'Referrer-Policy']) {
    assert.match(assets.slice(0, assets.indexOf('}')), new RegExp(header), `${header} on static assets`);
  }
  const csp = csps[0];
  const connect = csp.split(';').map((d) => d.trim()).find((d) => d.startsWith('connect-src'));
  assert.equal(connect, "connect-src 'self'");
  assert.match(csp, /frame-ancestors 'none'/);
  assert.match(conf, /location \/api\/shadow\/ \{/);
  assert.doesNotMatch(conf, /api\/upi/);
});

test('portfolio opens owner-private by default and only a test harness may opt into demo', () => {
  const page = read('src/pages/PortfolioPage.tsx');
  assert.match(page, /const ALLOW_SYNTHETIC = /);
  assert.match(page, /__ACASH_ALLOW_SYNTHETIC_DEMO__/);
  assert.match(page, /useState<DataMode>\(ALLOW_SYNTHETIC \? 'SYNTHETIC_DEMO' : 'OWNER_PRIVATE_READ_ONLY'\)/);
  assert.match(page, /\{ALLOW_SYNTHETIC && \(/);
  assert.doesNotMatch(page, /import\.meta\.env/);
  assert.match(read('src/services/upiRepository.ts'), /never substituted for owner data/);
});

test('portfolio uses accessible tabs and keeps every section in its own panel', () => {
  const tabs = read('src/components/portfolio/PortfolioTabs.tsx');
  assert.match(tabs, /role="tablist"/);
  assert.match(tabs, /role="tab"/);
  assert.match(tabs, /role="tabpanel"/);
  assert.match(tabs, /aria-selected=\{selected\}/);
  assert.match(tabs, /aria-controls=\{`panel-\$\{id\}`\}/);
  assert.match(tabs, /hidden=\{active !== id\}/);
  assert.match(tabs, /event\.key === 'ArrowRight'/);
  assert.match(tabs, /tabIndex=\{selected \? 0 : -1\}/);
  assert.match(tabs, /'overview', 'holdings', 'transactions', 'market', 'planning', 'data'/);

  const page = read('src/pages/PortfolioPage.tsx');
  for (const id of ['overview', 'holdings', 'transactions', 'market', 'planning', 'data']) {
    assert.match(page, new RegExp(`<TabPanel id="${id}"`), id);
  }
  assert.equal((page.match(/<MarketRefreshPanel /g) || []).length, 1, 'market panel mounts once');
  assert.equal((page.match(/<TransactionJournalPanel \/>/g) || []).length, 1, 'journal mounts once');
  for (const section of ['overview', 'holdings', 'planning', 'data']) {
    assert.match(page, new RegExp(`section="${section}"`), section);
  }
});

test('market mode never claims a reconciled NAV or zero for unpriced instruments', () => {
  const page = read('src/pages/PortfolioPage.tsx');
  assert.match(page, /partial \? 'N\/A'/);
  assert.match(page, /ต่างช่วงเวลา/);
  assert.match(page, /ไม่ใช่ 0/);
  assert.match(page, /position_level_coverage/);
});

test('external cash stays outside the broker scope and is labelled mixed evidence', () => {
  const panel = read('src/components/portfolio/ExternalCashPanel.tsx');
  const service = read('src/services/wealth.ts');
  assert.match(service, /api\/upi\/wealth/);
  assert.match(service, /cache: 'no-store'/);
  assert.match(panel, /เงินสดนอกพอร์ต/);
  assert.match(panel, /เป้าหมายเงินสดนอกพอร์ต/);
  assert.match(panel, /ไม่ถูกนำไปคิดใน NAV ของโบรกเกอร์/);
  assert.match(panel, /mixed evidence/i);
  for (const banned of [/localStorage/, /sessionStorage/, /document\.cookie/]) {
    assert.doesNotMatch(panel + service, banned);
  }
});

test('classification coverage is shown without claiming a full universe', () => {
  const panel = read('src/components/portfolio/ExternalCashPanel.tsx');
  assert.match(panel, /การจัดประเภทสินทรัพย์/);
  assert.match(panel, /coverage_by_value/);
  assert.match(panel, /ไม่เดาจาก ticker/);
});
