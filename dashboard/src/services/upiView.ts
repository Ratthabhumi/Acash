// ACASH_UPI_VIEW_V1 contract: types, runtime validation, load-state classification and
// display formatting. Python is the calculation authority; amounts stay decimal strings and
// are never converted to floating point here. This module has no imports so the Node test
// runner can load it directly.

export const VIEW_SCHEMA = 'ACASH_UPI_VIEW_V1';
export const PRIVATE_ENDPOINT = 'http://127.0.0.1:8765/api/upi/view';
export const TOKEN_HEADER = 'X-ACASH-Session';

export type DataMode = 'SYNTHETIC_DEMO' | 'OWNER_PRIVATE_READ_ONLY';
export type Dec = string;

export interface Bucket {
  value: Dec;
  weight: Dec;
}

export interface AccountTotal {
  status: string;
  observed_total?: Dec | null;
  known_components?: Dec | null;
  difference?: Dec | null;
  tolerance?: Dec | null;
  currency?: string | null;
  fx_source_may_differ?: boolean | null;
}

export interface UpiAccount {
  account_ref: string;
  broker: string | null;
  role: string | null;
  base_currency: string | null;
  evidence_level: string;
  computed_value: Dec;
  observed_position_value: Dec;
  unclassified_holdings_value: Dec;
  cash_lines_observed: boolean;
  account_total: AccountTotal;
  sub_portfolio_totals: Array<Record<string, unknown>>;
  flags: string[];
}

export interface CapacityScenario {
  monthly_contribution_thb: Dec;
  residual_after_contribution_thb: Dec;
  months_to_reserve_target_from_residual: number | null;
  status: string;
}

export interface UpiView {
  view_schema: typeof VIEW_SCHEMA;
  data_mode: DataMode;
  view_sha256: string;
  report_metadata: {
    pack_version: string;
    pack_sha256: string;
    snapshot_id: string;
    snapshot_schema: string;
    report_type: 'FULL_REPORT' | 'EVIDENCE_ONLY_REPORT';
    report_currency: string;
    valuation_date: string;
    observed_at: string;
    observation_lag_days: number;
    valuation_age_days: number | null;
    valuation_stale: boolean;
    stale_after_days: number;
    support_state: string;
    unsupported_analyses: string[];
  };
  portfolio_overview: {
    computed_nav_ppds: Dec;
    observed_position_value: Dec;
    unclassified_holdings_value: Dec;
    total_best_evidence: Dec;
    computed_nav_is_total_best_evidence: false;
  };
  coverage: Record<string, string>;
  accounts: UpiAccount[];
  allocation: {
    by_sub_portfolio_best_evidence: Record<string, Bucket>;
    currency_exposure_best_evidence: Record<string, Bucket>;
    computed_by_classification: Record<string, Bucket> | null;
    computed_status: 'COMPUTED_SUBSET_PPDS' | 'NOT_COMPUTED_EVIDENCE_ONLY_REPORT';
  };
  concentration: {
    status: string;
    denominator: string;
    key_policy: string;
    top1_weight: Dec | null;
    unclassified_share: Dec | null;
    hhi_identified_securities: Dec | null;
    top_holdings: Array<{ key: string; weight: Dec }>;
  };
  security_identity: Array<{ security_id: string; identity_status: string; instrument_type: string | null }>;
  financial_capacity: {
    capacity_status: string;
    monthly_surplus_thb: Dec;
    reserve: Record<string, string>;
    scenarios: CapacityScenario[];
    quant_budget: Record<string, unknown>;
  };
  quant_workspace: Record<string, unknown>;
  decision_status: { conclusion: string; reasons: string[]; orders_generated: 0 };
  governance: { observation_authority: Record<string, string>; flags: Record<string, unknown> };
  data_quality: { performance_status: string; market_session_status: string; reason_codes: string[] };
}

export class UpiViewError extends Error {}

const DECIMAL = /^-?\d+(\.\d+)?$/;
type Obj = Record<string, unknown>;

function fail(path: string, why: string): never {
  throw new UpiViewError(`VIEW_CONTRACT_INVALID: ${path} ${why}`);
}

function obj(v: unknown, path: string): Obj {
  if (typeof v !== 'object' || v === null || Array.isArray(v)) fail(path, 'must be an object');
  return v as Obj;
}

function arr(v: unknown, path: string): unknown[] {
  if (!Array.isArray(v)) fail(path, 'must be an array');
  return v;
}

function str(o: Obj, key: string, path: string): string {
  const v = o[key];
  if (typeof v !== 'string' || v.length === 0) fail(`${path}.${key}`, 'must be a non-empty string');
  return v;
}

function dec(o: Obj, key: string, path: string): Dec {
  const v = o[key];
  if (typeof v !== 'string' || !DECIMAL.test(v)) fail(`${path}.${key}`, 'must be a decimal string');
  return v;
}

function optDec(o: Obj, key: string, path: string): void {
  if (o[key] !== null && o[key] !== undefined) dec(o, key, path);
}

function buckets(v: unknown, path: string): void {
  const o = obj(v, path);
  for (const [k, b] of Object.entries(o)) {
    const bo = obj(b, `${path}.${k}`);
    dec(bo, 'value', `${path}.${k}`);
    dec(bo, 'weight', `${path}.${k}`);
  }
}

export function parseUpiView(raw: unknown, expectedMode: DataMode): UpiView {
  const v = obj(raw, 'view');
  if (v.view_schema !== VIEW_SCHEMA) fail('view.view_schema', 'unsupported');
  if (v.data_mode !== expectedMode) fail('view.data_mode', `must be ${expectedMode}`);
  str(v, 'view_sha256', 'view');

  const meta = obj(v.report_metadata, 'report_metadata');
  for (const k of ['pack_sha256', 'snapshot_id', 'snapshot_schema', 'report_currency', 'valuation_date', 'observed_at']) {
    str(meta, k, 'report_metadata');
  }
  if (meta.report_type !== 'FULL_REPORT' && meta.report_type !== 'EVIDENCE_ONLY_REPORT') {
    fail('report_metadata.report_type', 'unsupported');
  }
  if (typeof meta.valuation_stale !== 'boolean') fail('report_metadata.valuation_stale', 'must be boolean');

  const ov = obj(v.portfolio_overview, 'portfolio_overview');
  for (const k of ['computed_nav_ppds', 'observed_position_value', 'unclassified_holdings_value', 'total_best_evidence']) {
    dec(ov, k, 'portfolio_overview');
  }
  if (ov.computed_nav_is_total_best_evidence !== false) {
    fail('portfolio_overview.computed_nav_is_total_best_evidence', 'must be false');
  }

  arr(v.accounts, 'accounts').forEach((a, i) => {
    const p = `accounts[${i}]`;
    const ao = obj(a, p);
    str(ao, 'account_ref', p);
    str(ao, 'evidence_level', p);
    for (const k of ['computed_value', 'observed_position_value', 'unclassified_holdings_value']) dec(ao, k, p);
    const t = obj(ao.account_total, `${p}.account_total`);
    str(t, 'status', `${p}.account_total`);
    for (const k of ['observed_total', 'known_components', 'difference', 'tolerance']) optDec(t, k, `${p}.account_total`);
    arr(ao.flags, `${p}.flags`);
  });

  const al = obj(v.allocation, 'allocation');
  buckets(al.by_sub_portfolio_best_evidence, 'allocation.by_sub_portfolio_best_evidence');
  buckets(al.currency_exposure_best_evidence, 'allocation.currency_exposure_best_evidence');
  if (al.computed_status === 'COMPUTED_SUBSET_PPDS') {
    buckets(al.computed_by_classification, 'allocation.computed_by_classification');
  } else if (al.computed_status !== 'NOT_COMPUTED_EVIDENCE_ONLY_REPORT' || al.computed_by_classification !== null) {
    fail('allocation.computed_status', 'inconsistent with computed_by_classification');
  }
  if ((meta.report_type === 'EVIDENCE_ONLY_REPORT') !== (al.computed_status === 'NOT_COMPUTED_EVIDENCE_ONLY_REPORT')) {
    fail('allocation.computed_status', 'inconsistent with report_type');
  }

  const conc = obj(v.concentration, 'concentration');
  str(conc, 'status', 'concentration');
  for (const k of ['top1_weight', 'unclassified_share', 'hhi_identified_securities']) optDec(conc, k, 'concentration');
  arr(conc.top_holdings, 'concentration.top_holdings').forEach((h, i) =>
    dec(obj(h, `concentration.top_holdings[${i}]`), 'weight', `concentration.top_holdings[${i}]`));

  const cap = obj(v.financial_capacity, 'financial_capacity');
  dec(cap, 'monthly_surplus_thb', 'financial_capacity');
  arr(cap.scenarios, 'financial_capacity.scenarios').forEach((s, i) => {
    const so = obj(s, `financial_capacity.scenarios[${i}]`);
    dec(so, 'monthly_contribution_thb', `financial_capacity.scenarios[${i}]`);
    dec(so, 'residual_after_contribution_thb', `financial_capacity.scenarios[${i}]`);
  });

  const ds = obj(v.decision_status, 'decision_status');
  if (ds.orders_generated !== 0) fail('decision_status.orders_generated', 'must be 0');
  arr(ds.reasons, 'decision_status.reasons');
  const gov = obj(v.governance, 'governance');
  const auth = obj(gov.observation_authority, 'governance.observation_authority');
  if (auth.trading_authority !== 'NONE') fail('governance.observation_authority.trading_authority', 'must be NONE');
  const expected = expectedMode === 'OWNER_PRIVATE_READ_ONLY' ? 'OWNER_PRIVATE_READ_ONLY_OBSERVATION' : 'NOT_REQUIRED_SYNTHETIC_FIXTURE';
  if (auth.observation_authority !== expected) fail('governance.observation_authority', 'inconsistent with data_mode');
  obj(v.data_quality, 'data_quality');
  obj(v.coverage, 'coverage');
  return v as unknown as UpiView;
}

export type LoadStatus =
  | 'READY'
  | 'READY_WITH_WARNINGS'
  | 'STALE'
  | 'NO_REPORT'
  | 'AUTHORIZATION_REQUIRED'
  | 'INVALID_REPORT'
  | 'SERVICE_UNAVAILABLE';

export type LoadState =
  | { status: 'READY' | 'READY_WITH_WARNINGS' | 'STALE'; view: UpiView; warnings: string[] }
  | { status: 'NO_REPORT' | 'AUTHORIZATION_REQUIRED' | 'INVALID_REPORT' | 'SERVICE_UNAVAILABLE'; detail: string };

const AUTHORITY_CODES = ['PRIVATE_OBSERVATION_AUTHORIZATION_NOT_REQUIRED', 'OWNER_PRIVATE_OBSERVATION_AUTHORIZED'];

export function classifyView(raw: unknown, mode: DataMode): LoadState {
  let view: UpiView;
  try {
    view = parseUpiView(raw, mode);
  } catch (err) {
    return { status: 'INVALID_REPORT', detail: err instanceof UpiViewError ? err.message : 'VIEW_CONTRACT_INVALID' };
  }
  const warnings = view.data_quality.reason_codes.filter((c) => !AUTHORITY_CODES.includes(c));
  if (view.report_metadata.valuation_stale) return { status: 'STALE', view, warnings };
  return { status: warnings.length ? 'READY_WITH_WARNINGS' : 'READY', view, warnings };
}

export function classifyResponse(httpStatus: number, body: unknown): LoadState {
  const code = typeof body === 'object' && body !== null ? String((body as Obj).status ?? '') : '';
  const extra = typeof body === 'object' && body !== null && (body as Obj).odr_state ? ` (${String((body as Obj).odr_state)})` : '';
  if (httpStatus === 200) return classifyView(body, 'OWNER_PRIVATE_READ_ONLY');
  if (httpStatus === 401 || httpStatus === 403) return { status: 'AUTHORIZATION_REQUIRED', detail: `${code || 'FORBIDDEN'}${extra}` };
  if (httpStatus === 404 && code === 'NO_REPORT') return { status: 'NO_REPORT', detail: code };
  if (httpStatus === 422) return { status: 'INVALID_REPORT', detail: code || 'INVALID_REPORT' };
  return { status: 'SERVICE_UNAVAILABLE', detail: `HTTP_${httpStatus}` };
}

function groupThousands(intPart: string): string {
  return intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

export const NOT_ESTABLISHED = 'NOT ESTABLISHED';

export function formatDec(value: Dec | null | undefined, unit?: string): string {
  if (value === null || value === undefined) return NOT_ESTABLISHED;
  if (!DECIMAL.test(value)) return 'INVALID';
  const neg = value.startsWith('-');
  const [i, f] = (neg ? value.slice(1) : value).split('.');
  const body = `${neg ? '-' : ''}${groupThousands(i)}${f !== undefined ? `.${f}` : ''}`;
  return unit ? `${body} ${unit}` : body;
}

// Chart geometry only: maps an already-qualified decimal (a Python weight, or part/whole of
// Python values) to a bar fraction in [0, 1]. Never use the result as a displayed figure.
export function barFraction(part: Dec | null | undefined, whole: Dec | null | undefined = '1'): number {
  if (part == null || whole == null || !DECIMAL.test(part) || !DECIMAL.test(whole)) return 0;
  const p = Number(part);
  const w = Number(whole);
  if (!(w > 0) || !(p > 0)) return 0;
  return Math.min(1, p / w);
}

export function formatWeight(value: Dec | null | undefined): string {
  if (value === null || value === undefined) return NOT_ESTABLISHED;
  if (!DECIMAL.test(value)) return 'INVALID';
  const neg = value.startsWith('-');
  const [i, f = ''] = (neg ? value.slice(1) : value).split('.');
  const digits = (f + '00').slice(0, Math.max(2, f.length));
  const whole = `${i}${digits.slice(0, 2)}`.replace(/^0+(?=\d)/, '');
  const frac = digits.slice(2);
  return `${neg ? '-' : ''}${whole}${frac ? `.${frac}` : ''}%`;
}
