import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Lock, RefreshCw, ShieldAlert } from 'lucide-react';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { SkeletonLoader } from '../components/common/SkeletonLoader';
import { SyntheticVariant, upiRepository } from '../services/upiRepository';
import { Bucket, DataMode, LoadState, UpiView, formatDec, formatWeight } from '../services/upiView';

const STATUS_HELP: Record<string, string> = {
  AUTHORIZATION_REQUIRED: 'ODR-001 is not RATIFIED, or the session token is wrong or from an earlier server start. Restart START-DASHBOARD.bat private for a new token.',
  NO_REPORT: 'The service is running but data/private/out/upi_view.json does not exist yet. Generate it with acash.invest.upi_view (see the runbook).',
  INVALID_REPORT: 'The private view failed contract validation. Regenerate it from the current wealth pack.',
  SERVICE_UNAVAILABLE: 'The loopback service is not reachable on 127.0.0.1:8765. Start it with START-DASHBOARD.bat private.',
};

const Section: React.FC<{ title: string; note?: string; children: React.ReactNode }> = ({ title, note, children }) => (
  <section className="bg-surface border border-default rounded-md p-4 space-y-3">
    <div>
      <h2 className="text-sm font-semibold text-primary">{title}</h2>
      {note && <p className="text-xs text-secondary mt-0.5">{note}</p>}
    </div>
    {children}
  </section>
);

const BucketTable: React.FC<{ rows: Record<string, Bucket>; ccy: string }> = ({ rows, ccy }) => (
  <table className="w-full text-xs font-mono-code">
    <thead>
      <tr className="text-left text-muted">
        <th className="py-1">Bucket</th>
        <th className="py-1 text-right">Value ({ccy})</th>
        <th className="py-1 text-right">Weight</th>
      </tr>
    </thead>
    <tbody>
      {Object.entries(rows).map(([k, b]) => (
        <tr key={k} className="border-t border-subtle">
          <td className="py-1 text-primary">{k}</td>
          <td className="py-1 text-right">{formatDec(b.value)}</td>
          <td className="py-1 text-right">{formatWeight(b.weight)}</td>
        </tr>
      ))}
    </tbody>
  </table>
);

const KeyValues: React.FC<{ values: Record<string, unknown> }> = ({ values }) => (
  <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-xs font-mono-code">
    {Object.entries(values).map(([k, v]) => (
      <div key={k} className="flex justify-between gap-3 border-b border-subtle py-1">
        <dt className="text-muted">{k}</dt>
        <dd className="text-primary text-right break-all">{v === null || v === undefined ? 'NOT ESTABLISHED' : Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : String(v)}</dd>
      </div>
    ))}
  </dl>
);

const PortfolioReport: React.FC<{ view: UpiView }> = ({ view }) => {
  const meta = view.report_metadata;
  const ccy = meta.report_currency;
  const ov = view.portfolio_overview;
  const evidenceOnly = meta.report_type === 'EVIDENCE_ONLY_REPORT';
  return (
    <div className="space-y-4">
      <Section title="Total Wealth" note="Computed NAV (PPDS quantity × price + settled cash) is not the total best evidence. Broker totals are compared, never added.">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          <MetricCard label="Total best evidence" value={formatDec(ov.total_best_evidence)} subValue={`${ccy} · computed + observed + unclassified`} />
          <MetricCard label="Computed NAV (PPDS)" value={formatDec(ov.computed_nav_ppds)} subValue={evidenceOnly ? 'No quantity or cash line carries value' : `${ccy} · computed subset only`} />
          <MetricCard label="Observed value-only positions" value={formatDec(ov.observed_position_value)} subValue={`${ccy} · broker-displayed, not computed`} />
          <MetricCard label="Unclassified holdings value" value={formatDec(ov.unclassified_holdings_value)} subValue={`${ccy} · broker total minus identified lines`} />
        </div>
        <KeyValues values={{
          report_type: meta.report_type, valuation_date: meta.valuation_date, observed_at: meta.observed_at,
          observation_lag_days: meta.observation_lag_days, valuation_age_days: meta.valuation_age_days,
          valuation_stale: meta.valuation_stale, support_state: meta.support_state,
          performance: view.data_quality.performance_status, market_session: view.data_quality.market_session_status,
          ...view.coverage,
        }} />
        {meta.unsupported_analyses.length > 0 && (
          <p className="text-xs text-secondary">Not computed in this report: {meta.unsupported_analyses.join(', ')}</p>
        )}
      </Section>

      <Section title="Accounts & Holdings" note="One row per observed account. Differences use the precision the broker displays.">
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono-code">
            <thead>
              <tr className="text-left text-muted">
                <th className="py-1">Account</th><th>Role</th><th>Evidence</th>
                <th className="text-right">Computed</th><th className="text-right">Value-only</th>
                <th className="text-right">Unclassified</th><th>Account total</th><th className="text-right">Difference</th>
              </tr>
            </thead>
            <tbody>
              {view.accounts.map((a) => (
                <tr key={a.account_ref} className="border-t border-subtle align-top">
                  <td className="py-1 text-primary">
                    <details>
                      <summary className="cursor-pointer">{a.account_ref}</summary>
                      <div className="text-muted mt-1 space-y-0.5">
                        <div>broker {a.broker ?? 'NOT ESTABLISHED'} · base {a.base_currency ?? 'NOT ESTABLISHED'}</div>
                        <div>cash lines observed: {String(a.cash_lines_observed)}</div>
                        <div>flags: {a.flags.join(', ') || '-'}</div>
                        {a.sub_portfolio_totals.length > 0 && <div>sub-portfolio totals: {JSON.stringify(a.sub_portfolio_totals)}</div>}
                      </div>
                    </details>
                  </td>
                  <td>{a.role ?? 'NOT ESTABLISHED'}</td>
                  <td>{a.evidence_level}</td>
                  <td className="text-right">{formatDec(a.computed_value)}</td>
                  <td className="text-right">{formatDec(a.observed_position_value)}</td>
                  <td className="text-right">{formatDec(a.unclassified_holdings_value)}</td>
                  <td><StatusBadge status={a.account_total.status} /></td>
                  <td className="text-right">{a.account_total.difference === undefined ? '-' : formatDec(a.account_total.difference, a.account_total.currency ?? undefined)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Allocation & Concentration" note={`Concentration status ${view.concentration.status}: weights are a lower bound while unclassified value is present.`}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div><h3 className="text-xs font-semibold text-secondary mb-1">By sub-portfolio (best evidence)</h3><BucketTable rows={view.allocation.by_sub_portfolio_best_evidence} ccy={ccy} /></div>
          <div><h3 className="text-xs font-semibold text-secondary mb-1">Currency exposure (best evidence)</h3><BucketTable rows={view.allocation.currency_exposure_best_evidence} ccy={ccy} /></div>
          <div>
            <h3 className="text-xs font-semibold text-secondary mb-1">Computed by classification</h3>
            {view.allocation.computed_by_classification
              ? <BucketTable rows={view.allocation.computed_by_classification} ccy={ccy} />
              : <StatusBadge status={view.allocation.computed_status} />}
          </div>
          <div className="space-y-2">
            <KeyValues values={{
              top1_weight: formatWeight(view.concentration.top1_weight),
              unclassified_share: formatWeight(view.concentration.unclassified_share),
              hhi_identified_securities: view.concentration.hhi_identified_securities,
              denominator: view.concentration.denominator,
            }} />
            <ul className="text-xs font-mono-code space-y-0.5">
              {view.security_identity.map((s) => (
                <li key={s.security_id} className="flex justify-between"><span>{s.security_id}</span><StatusBadge status={s.identity_status} /></li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      <Section title="Financial Capacity" note="Illustrative planning scenarios from the capacity planner. Not advice and not an instruction to transfer money.">
        <KeyValues values={{
          capacity_status: view.financial_capacity.capacity_status,
          monthly_surplus_thb: formatDec(view.financial_capacity.monthly_surplus_thb),
          ...view.financial_capacity.reserve,
        }} />
        <table className="w-full text-xs font-mono-code">
          <thead><tr className="text-left text-muted"><th className="py-1">Contribution (THB)</th><th className="text-right">Residual</th><th className="text-right">Months to reserve target</th><th>Status</th></tr></thead>
          <tbody>
            {view.financial_capacity.scenarios.map((s) => (
              <tr key={s.monthly_contribution_thb} className="border-t border-subtle">
                <td className="py-1">{formatDec(s.monthly_contribution_thb)}</td>
                <td className="text-right">{formatDec(s.residual_after_contribution_thb)}</td>
                <td className="text-right">{s.months_to_reserve_target_from_residual ?? 'NOT ESTABLISHED'}</td>
                <td><StatusBadge status={s.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        <KeyValues values={view.financial_capacity.quant_budget} />
      </Section>

      <Section title="Decision, Governance & Evidence" note="Read-only decision support. No orders, transfers or authority are produced.">
        <div className="flex items-center gap-2">
          <StatusBadge status={view.decision_status.conclusion} size="md" />
          <span className="text-xs text-secondary font-mono-code">orders generated: {view.decision_status.orders_generated}</span>
        </div>
        <ul className="text-xs list-disc pl-5 space-y-0.5 text-primary">
          {view.decision_status.reasons.map((r) => <li key={r}>{r}</li>)}
        </ul>
        <KeyValues values={view.governance.observation_authority} />
        <details className="text-xs">
          <summary className="cursor-pointer text-secondary">Governance flags, quant workspace and provenance</summary>
          <div className="mt-2 space-y-2">
            <KeyValues values={view.governance.flags} />
            <KeyValues values={view.quant_workspace} />
            <KeyValues values={{ pack_version: meta.pack_version, pack_sha256: meta.pack_sha256, view_sha256: view.view_sha256,
              snapshot_id: meta.snapshot_id, snapshot_schema: meta.snapshot_schema }} />
          </div>
        </details>
      </Section>
    </div>
  );
};

export const PortfolioPage: React.FC = () => {
  const [mode, setMode] = useState<DataMode>('SYNTHETIC_DEMO');
  const [variant, setVariant] = useState<SyntheticVariant>('FULL_REPORT');
  const [token, setToken] = useState('');
  const [state, setState] = useState<LoadState | null>(null);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const switchMode = (next: DataMode) => {
    abortRef.current?.abort();
    setState(null);
    setToken('');
    setLoading(false);
    setMode(next);
  };

  useEffect(() => {
    if (mode === 'SYNTHETIC_DEMO') setState(upiRepository.loadSynthetic(variant));
  }, [mode, variant]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const connect = useCallback(async (value?: string) => {
    const session = value ?? token;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setState(null);
    const timer = window.setTimeout(() => controller.abort(), 8000);
    const result = await upiRepository.loadOwnerPrivate(session, controller.signal);
    window.clearTimeout(timer);
    if (abortRef.current === controller) {
      setState(result);
      setLoading(false);
      if (result.status === 'AUTHORIZATION_REQUIRED') setToken('');
    }
  }, [token]);

  const ready = state && 'view' in state;
  return (
    <div className="space-y-4 max-w-7xl">
      <div className="bg-surface border border-default rounded-md p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-base font-semibold text-primary">Portfolio Intelligence</h1>
            <p className="text-xs text-secondary">Read-only view of the Python wealth pack. All figures are computed in Python; this page only displays them.</p>
          </div>
          <div className="flex gap-2" role="group" aria-label="Data mode">
            {(['SYNTHETIC_DEMO', 'OWNER_PRIVATE_READ_ONLY'] as DataMode[]).map((m) => (
              <button key={m} onClick={() => switchMode(m)} aria-pressed={mode === m}
                className={`text-xs px-3 py-1.5 rounded border font-mono-code ${mode === m ? 'bg-accent text-white border-transparent' : 'border-default text-secondary hover:bg-surface-muted'}`}>
                {m.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>
        {mode === 'SYNTHETIC_DEMO' ? (
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <StatusBadge status="DEMO_DATA" size="md" />
            <span className="text-secondary">SYNTHETIC DEMO · public fixture · not owner data</span>
            <select value={variant} onChange={(e) => setVariant(e.target.value as SyntheticVariant)} aria-label="Synthetic report"
              className="ml-auto text-xs bg-surface border border-default rounded px-2 py-1">
              <option value="FULL_REPORT">Full report fixture</option>
              <option value="EVIDENCE_ONLY_REPORT">Evidence-only fixture</option>
            </select>
          </div>
        ) : (
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2 text-secondary">
              <Lock className="w-3.5 h-3.5" />
              <span>OWNER PRIVATE · READ-ONLY · loopback only. Requires ODR-001 RATIFIED and the local view service started with <code className="font-mono-code">uv run python -m acash.dashboard_api.private_view_server</code>.</span>
            </div>
            <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); void connect(); }}>
              <input type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); if (e.currentTarget.value && !loading) void connect(e.currentTarget.value); } }}
                placeholder="Session token printed by the local service" aria-label="Session token"
                className="flex-1 min-w-[16rem] bg-surface border border-default rounded px-2 py-1 font-mono-code" />
              <button type="submit" disabled={!token || loading}
                className="inline-flex items-center gap-1 px-3 py-1 rounded border border-default text-secondary hover:bg-surface-muted disabled:opacity-50">
                <RefreshCw className="w-3.5 h-3.5" /> Load
              </button>
              {ready && (
                <button type="button" onClick={() => switchMode('OWNER_PRIVATE_READ_ONLY')}
                  className="px-3 py-1 rounded border border-default text-secondary hover:bg-surface-muted">Clear</button>
              )}
            </form>
          </div>
        )}
        {state && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <StatusBadge status={state.status} size="md" />
            {'detail' in state && <span className="text-secondary font-mono-code">{state.detail}</span>}
            {'warnings' in state && state.warnings.length > 0 && (
              <span className="text-secondary font-mono-code">{state.warnings.join(' · ')}</span>
            )}
          </div>
        )}
      </div>

      {loading && <SkeletonLoader className="h-40 w-full" />}
      {!loading && state && 'view' in state && <PortfolioReport view={state.view} />}
      {!loading && state && !('view' in state) && (
        <div className="bg-surface border border-default rounded-md p-6 flex items-start gap-3 text-sm">
          <ShieldAlert className="w-5 h-5 text-muted shrink-0" />
          <div className="space-y-1">
            <div className="font-semibold text-primary">{state.status.replace(/_/g, ' ')}</div>
            <div className="text-xs text-secondary">{STATUS_HELP[state.status]}</div>
            <div className="text-xs text-secondary">No figures are shown. Synthetic data is never substituted for owner data.</div>
          </div>
        </div>
      )}
      {!loading && !state && mode === 'OWNER_PRIVATE_READ_ONLY' && (
        <div className="bg-surface border border-default rounded-md p-6 text-xs text-secondary">
          AUTHORIZATION REQUIRED · enter the session token from the local service to load the owner-private view.
        </div>
      )}
    </div>
  );
};
