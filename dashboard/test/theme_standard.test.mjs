import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * ACASH Warm Neutral Standard theme regression.
 *
 * Guards the structural contract that was ratified for the dashboard redesign:
 *  - Canonical light/dark hex values are the single authority (verbatim in index.css).
 *  - All structural colors flow through CSS custom properties; nothing structural
 *    is hard-coded as slate/gray utility classes anymore.
 *  - Dark mode is class-driven (`darkMode: 'class'`) so the `.dark` token block
 *    flips the whole surface at once.
 *  - Semantic status colors (emerald/rose/amber/blue) are preserved verbatim so
 *    health/verdict signals remain unchanged.
 *  - The shadow page's N/A null guards are preserved.
 *
 * This is a STATIC contract test: it asserts on source bytes, not rendered output.
 */

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, '..');

const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf8');

const indexCss = read('src/index.css');
const tailwindCfg = read('tailwind.config.js');

const LIGHT_TOKENS = {
  '--bg-app': '#F5F3EE',
  '--bg-surface': '#FBFAF7',
  '--bg-surface-muted': '#EFEDE7',
  '--border-default': '#D8D3C8',
  '--text-primary': '#171613',
  '--text-secondary': '#6F6B61',
  '--text-muted': '#9A958A',
  '--accent': '#78836B',
  '--accent-hover': '#6A755E',
  '--accent-subtle': '#E5E8DF',
};

const DARK_TOKENS = {
  '--bg-app': '#141412',
  '--bg-surface': '#1C1B19',
  '--bg-surface-muted': '#24231F',
  '--border-default': '#393731',
  '--text-primary': '#F5F3EE',
  '--text-secondary': '#B6B1A7',
  '--text-muted': '#817D74',
  '--accent': '#8F9B7F',
  '--accent-hover': '#A1AC92',
  '--accent-subtle': '#2A2F26',
};

function assertBlock(block, tokens, label) {
  for (const [prop, hex] of Object.entries(tokens)) {
    const re = new RegExp(`${prop}:\\s*${hex}\\s*;`);
    assert.match(block, re, `${label} must define ${prop} = ${hex}`);
  }
}

test('LIGHT theme tokens are the canonical verbatim hex values in :root', () => {
  assertBlock(indexCss, LIGHT_TOKENS, 'light');
});

test('DARK theme tokens are the canonical verbatim hex values in .dark', () => {
  // Only assert inside the .dark block, not the :root block.
  const darkStart = indexCss.indexOf('.dark {');
  const nextRoot = indexCss.indexOf('}', darkStart);
  const darkBlock = indexCss.slice(darkStart, nextRoot + 1);
  assert.notEqual(darkStart, -1, 'index.css must define a .dark block');
  assertBlock(darkBlock, DARK_TOKENS, 'dark');
});

test('RGB triplets exist so Tailwind <alpha-value> modifiers can resolve', () => {
  for (const prop of ['--bg-app-rgb', '--bg-surface-rgb', '--bg-surface-muted-rgb', '--border-default-rgb', '--text-primary-rgb', '--text-secondary-rgb', '--text-muted-rgb', '--accent-rgb', '--accent-hover-rgb', '--accent-subtle-rgb']) {
    assert.match(indexCss, new RegExp(`${prop}:\\s*\\d+(\\s+\\d+){2}\\s*;`), `${prop} must be an rgb triplet in :root`);
  }
});

test('Tailwind semantic aliases route through CSS custom properties', () => {
  assert.match(tailwindCfg, /darkMode:\s*'class'/, "darkMode must be 'class'");
  for (const alias of ['app', 'surface', 'border', 'primary', 'secondary', 'muted', 'accent']) {
    assert.match(tailwindCfg, new RegExp(`${alias}:`), `tailwind config must define the ${alias} color alias`);
  }
  assert.match(tailwindCfg, /rgb\(var\(--bg-app-rgb\) \/ <alpha-value>\)/, 'app must resolve through var(--bg-app-rgb)');
  assert.match(tailwindCfg, /rgb\(var\(--accent-rgb\) \/ <alpha-value>\)/, 'accent must resolve through var(--accent-rgb)');
});

test('body and scrollbar are theme-driven via CSS custom properties', () => {
  assert.match(indexCss, /html\s*{[^}]*background-color:\s*var\(--bg-app\)/s, 'html must use var(--bg-app)');
  assert.match(indexCss, /body\s*{[^}]*background-color:\s*var\(--bg-app\)/s, 'body must use var(--bg-app)');
  assert.match(indexCss, /::-webkit-scrollbar-thumb\s*{[^}]*background:\s*var\(--border-strong\)/s, 'scrollbar must use var(--border-strong)');
});

test('app surfaces are semantic, not hard-coded slate backgrounds', async () => {
  const files = [
    'index.html',
    'src/main.tsx',
    'src/App.tsx',
    'src/components/layout/AppShell.tsx',
    'src/components/layout/Header.tsx',
    'src/components/layout/Sidebar.tsx',
    'src/components/layout/CommandPalette.tsx',
    'src/components/common/StatusBadge.tsx',
    'src/components/common/MetricCard.tsx',
    'src/components/common/SkeletonLoader.tsx',
    'src/components/common/EmptyState.tsx',
    'src/components/common/CopyablePill.tsx',
    'src/components/charts/EquityDrawdownChart.tsx',
    'src/pages/OverviewPage.tsx',
    'src/pages/TradesPage.tsx',
    'src/pages/EvidencePage.tsx',
    'src/pages/ValidationPage.tsx',
    'src/pages/ShadowTournamentPage.tsx',
  ];
  for (const rel of files) {
    const src = read(rel);
    assert.doesNotMatch(src, /slate-|gray-|charcoal|enterprise-border/, `${rel} must have no structural slate/gray/charcoal/enterprise-border classes`);
  }
});

test('semantic status colors (rose/emerald/amber/blue) remain present for health/verdicts', () => {
  const statusBadge = read('src/components/common/StatusBadge.tsx');
  assert.match(statusBadge, /bg-rose-50 dark:bg-rose-950\/40/, 'StatusBadge must keep the rose FAIL palette');
  assert.match(statusBadge, /bg-emerald-50 dark:bg-emerald-950\/40/, 'StatusBadge must keep the emerald PASS palette');
  assert.match(statusBadge, /bg-amber-50 dark:bg-amber-950\/40/, 'StatusBadge must keep the amber PENDING palette');
  assert.match(statusBadge, /bg-blue-50 dark:bg-blue-950\/40/, 'StatusBadge must keep the blue INFO palette');

  const shadow = read('src/pages/ShadowTournamentPage.tsx');
  assert.match(shadow, /bg-emerald-50 dark:bg-emerald-950\/40/, 'Shadow feed badge must keep the emerald HEALTHY palette');
  assert.match(shadow, /bg-amber-50 dark:bg-amber-950\/40/, 'Shadow feed badge must keep the amber STALE palette');
  assert.match(shadow, /bg-rose-50 dark:bg-rose-950\/40/, 'Shadow feed badge must keep the rose HALTED palette');
});

test('shadow page N/A null guards are preserved', () => {
  const shadow = read('src/pages/ShadowTournamentPage.tsx');
  assert.match(shadow, /metrics\.riskUtilizationPct !== null \? .*: '—'/, 'Risk Util. null guard must remain');
  assert.match(shadow, /metrics\.exposurePct !== null \? .*: '—'/, 'Exposure null guard must remain');
  assert.match(shadow, /metrics\.winRatePct !== null \? .*: '— \(n<2\)'/, 'Win Rate null guard must remain');
  assert.match(shadow, /metrics\.durationSeconds !== null \? formatDuration\(metrics\.durationSeconds\) : '—'/, 'Runtime null guard must remain');
});

test('chart uses theme-driven SVG tokens, not isDark branches', () => {
  const chart = read('src/components/charts/EquityDrawdownChart.tsx');
  assert.doesNotMatch(chart, /isDark/, 'chart must not depend on useTheme/isDark');
  assert.doesNotMatch(chart, /useTheme/, 'chart must not import useTheme');
  assert.match(chart, /stroke="var\(--chart-net\)"/, 'net equity line must use var(--chart-net)');
  assert.match(chart, /fill="var\(--chart-net\)"/, 'net marker must use var(--chart-net)');
  assert.match(chart, /var\(--chart-grid\)/, 'gridlines must use var(--chart-grid)');
  assert.match(chart, /var\(--chart-crosshair\)/, 'crosshair must use var(--chart-crosshair)');
  assert.match(chart, /var\(--popover-bg\)/, 'tooltip must use popover tokens');
  assert.match(chart, /#f43f5e/, 'drawdown must remain the semantic rose #f43f5e');
});