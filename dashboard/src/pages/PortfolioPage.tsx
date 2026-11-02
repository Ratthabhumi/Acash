import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertOctagon, AlertTriangle, ChevronDown, Info, Lock, RefreshCw, Search, ShieldAlert, ShieldCheck } from 'lucide-react';
import { StatusBadge } from '../components/common/StatusBadge';
import { SkeletonLoader } from '../components/common/SkeletonLoader';
import { BarList, BarRow, ChartCard, Segment, SimpleTable, StackedBar, Tone } from '../components/charts/PortfolioCharts';
import { SyntheticVariant, upiRepository } from '../services/upiRepository';
import { Finding, Severity, findingsFor } from '../services/upiFindings';
import { DataMode, LoadState, NOT_ESTABLISHED, UpiView, barFraction, formatDec, formatWeight } from '../services/upiView';

const STATUS_HELP: Record<string, string> = {
  AUTHORIZATION_REQUIRED: 'ODR-001 is not RATIFIED, or the session token is wrong or from an earlier server start. Restart START-DASHBOARD.bat private for a new token.',
  NO_REPORT: 'The service is running but data/private/out/upi_view.json does not exist yet. Generate it with acash.invest.upi_view (see the runbook).',
  INVALID_REPORT: 'The private view failed contract validation. Regenerate it from the current wealth pack.',
  SERVICE_UNAVAILABLE: 'The loopback service is not reachable on 127.0.0.1:8765. Start it with START-DASHBOARD.bat private.',
};

// Presentation ordering only (never displayed): sorts rows by a Python decimal string.
const byValueDesc = (a: string, b: string) => Number(b) - Number(a);
const isDecimal = (v: unknown): v is string => typeof v === 'string' && /^-?\d+(\.\d+)?$/.test(v);

const classTone = (key: string): Tone => {
  if (/UNCLASSIFIED|UNKNOWN/.test(key)) return 'unknown';
  if (key === 'CASH') return 'emerald';
  if (key.startsWith('CORE')) return 'accent';
  if (/SATELLITE|THEMATIC/.test(key)) return 'violet';
  return 'sky';
};

const humanize = (code: string) => code.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase());

const SectionHeader: React.FC<{ id: string; letter: string; title: string; note?: string }> = ({ id, letter, title, note }) => (
  <div className="flex items-baseline gap-3 pt-2">
    <span className="text-[11px] font-mono-code text-muted">{letter}</span>
    <div>
      <h2 id={id} className="text-base font-semibold text-primary">{title}</h2>
      {note && <p className="text-xs text-secondary mt-0.5 max-w-3xl">{note}</p>}
    </div>
  </div>
);

const SummaryCard: React.FC<{ label: string; value: string; unit?: string; subtitle: string; tone?: 'default' | 'good' | 'warn' | 'bad'; badge?: React.ReactNode }> = ({ label, value, unit, subtitle, tone = 'default', badge }) => {
  const edge = { default: 'border-l-accent', good: 'border-l-emerald-500', warn: 'border-l-amber-500', bad: 'border-l-rose-500' }[tone];
  const notEstablished = value === NOT_ESTABLISHED;
  return (
    <div className={`bg-surface border border-default border-l-4 ${edge} rounded-lg p-4 flex flex-col gap-1.5 min-w-0`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-secondary">{label}</span>
        {badge}
      </div>
      <div className={`font-mono-code tabular-nums tracking-tight ${notEstablished ? 'text-sm text-muted' : 'text-2xl font-semibold text-primary'}`}>
        {value}{unit && !notEstablished && <span className="text-xs font-normal text-muted ml-1.5">{unit}</span>}
      </div>
      <p className="text-[11px] leading-snug text-secondary">{subtitle}</p>
    </div>
  );
};

const KeyValues: React.FC<{ values: Record<string, unknown> }> = ({ values }) => (
  <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-xs font-mono-code">
    {Object.entries(values).map(([k, v]) => (
      <div key={k} className="flex justify-between gap-3 border-b border-subtle py-1">
        <dt className="text-muted">{k}</dt>
        <dd className="text-primary text-right break-all">{v === null || v === undefined ? NOT_ESTABLISHED : Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : String(v)}</dd>
      </div>
    ))}
  </dl>
);

const Disclosure: React.FC<{ title: string; children: React.ReactNode; defaultOpen?: boolean }> = ({ title, children, defaultOpen }) => (
  <details className="group bg-surface border border-default rounded-lg" open={defaultOpen}>
    <summary className="list-none [&::-webkit-details-marker]:hidden flex items-center gap-2 cursor-pointer select-none px-4 py-2.5 text-xs font-medium text-secondary hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-lg">
      <ChevronDown className="w-3.5 h-3.5 transition-transform group-open:rotate-180" aria-hidden />
      {title}
    </summary>
    <div className="px-4 pb-4 pt-1 space-y-3">{children}</div>
  </details>
);

const SEVERITY_STYLE: Record<Severity, { icon: React.ReactNode; label: string; cls: string }> = {
  CRITICAL: { icon: <AlertOctagon className="w-4 h-4 text-rose-500" aria-hidden />, label: 'Critical', cls: 'border-rose-500/40' },
  IMPORTANT: { icon: <AlertTriangle className="w-4 h-4 text-amber-500" aria-hidden />, label: 'Important', cls: 'border-amber-500/40' },
  INFO: { icon: <Info className="w-4 h-4 text-sky-500" aria-hidden />, label: 'Info', cls: 'border-default' },
};

const Findings: React.FC<{ findings: Finding[] }> = ({ findings }) => {
  if (findings.length === 0) return <p className="text-xs text-secondary">No open findings.</p>;
  const groups = (['CRITICAL', 'IMPORTANT', 'INFO'] as Severity[]).map((s) => [s, findings.filter((f) => f.severity === s)] as const);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 text-xs" aria-label="Findings by severity">
        {groups.map(([s, list]) => (
          <span key={s} className={`inline-flex items-center gap-1.5 px-2 py-1 rounded border ${SEVERITY_STYLE[s].cls}`}>
            {SEVERITY_STYLE[s].icon}{SEVERITY_STYLE[s].label}<span className="font-mono-code text-primary">{list.length}</span>
          </span>
        ))}
      </div>
      <ul className="space-y-2">
        {findings.map((f) => (
          <li key={f.code}>
            <details className={`group bg-surface border ${SEVERITY_STYLE[f.severity].cls} rounded-lg`} open={f.severity === 'CRITICAL'}>
              <summary className="list-none [&::-webkit-details-marker]:hidden flex items-start gap-2.5 cursor-pointer px-3 py-2.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-lg">
                {SEVERITY_STYLE[f.severity].icon}
                <span className="text-sm text-primary flex-1">{f.title}</span>
                <span className="hidden sm:inline text-[10px] font-mono-code text-muted">{f.code}</span>
              </summary>
              <div className="px-3 pb-3 pl-9 space-y-1.5 text-xs text-secondary">
                <p>{f.implication}</p>
                {f.action && <p><span className="text-primary">Next:</span> {f.action}</p>}
                <p className="font-mono-code text-muted break-words">{f.detail}</p>
              </div>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
};

const GovernanceStrip: React.FC<{ view: UpiView }> = ({ view }) => {
  const auth = view.governance.observation_authority;
  const items: Array<[string, string]> = [
    ['Data', view.data_mode === 'SYNTHETIC_DEMO' ? 'SYNTHETIC DEMO' : 'OWNER PRIVATE · READ-ONLY'],
    ['Observation', auth.observation_authority],
    ['ODR', auth.odr_state],
    ['Trading', auth.trading_authority],
    ['Capital', `USD ${auth.capital_authority_usd}`],
    ['Valuation date', view.report_metadata.valuation_date],
  ];
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] bg-surface-muted/60 border border-subtle rounded-lg px-3 py-2" aria-label="Governance summary">
      <ShieldCheck className="w-3.5 h-3.5 text-muted" aria-hidden />
      {items.map(([k, v]) => (
        <span key={k} className="whitespace-nowrap"><span className="text-muted">{k}</span> <span className="font-mono-code text-primary">{v}</span></span>
      ))}
      <span className="whitespace-nowrap"><span className="text-muted">Orders generated</span> <span className="font-mono-code text-primary">{view.decision_status.orders_generated}</span></span>
    </div>
  );
};

const AccountsAndHoldings: React.FC<{ view: UpiView; ccy: string }> = ({ view, ccy }) => {
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();
  const accounts = view.accounts.filter((a) => !q || [a.account_ref, a.broker, a.role, a.account_total.status].some((s) => s?.toLowerCase().includes(q)));
  const securities = view.security_identity.filter((s) => !q || [s.security_id, s.instrument_type, s.identity_status].some((x) => x?.toLowerCase().includes(q)));
  return (
    <div className="space-y-3">
      <label className="relative block max-w-sm">
        <span className="sr-only">Filter accounts and holdings</span>
        <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter accounts or holdings"
          className="w-full bg-surface border border-default rounded-md pl-8 pr-2 py-1.5 text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-accent" />
      </label>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {accounts.map((a) => {
          const t = a.account_total;
          return (
            <details key={a.account_ref} className="group bg-surface border border-default rounded-lg">
              <summary className="list-none [&::-webkit-details-marker]:hidden cursor-pointer px-4 py-3 space-y-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-lg">
                <div className="flex items-center gap-2 min-w-0">
                  <ChevronDown className="w-3.5 h-3.5 text-muted transition-transform group-open:rotate-180 shrink-0" aria-hidden />
                  <span className="font-mono-code text-sm text-primary truncate">{a.account_ref}</span>
                  <span className="text-[11px] text-muted truncate">{a.role ?? NOT_ESTABLISHED} · {a.base_currency ?? NOT_ESTABLISHED}</span>
                  <span className="ml-auto"><StatusBadge status={t.status} /></span>
                </div>
                <dl className="grid grid-cols-3 gap-2 text-[11px]">
                  {([['Computed', a.computed_value], ['Value-only', a.observed_position_value], ['Unclassified', a.unclassified_holdings_value]] as const).map(([k, v]) => (
                    <div key={k}><dt className="text-muted">{k}</dt><dd className="font-mono-code text-primary tabular-nums">{formatDec(v)}</dd></div>
                  ))}
                </dl>
              </summary>
              <div className="px-4 pb-4 space-y-2 text-xs">
                <KeyValues values={{
                  broker: a.broker, evidence_level: a.evidence_level, cash_lines_observed: a.cash_lines_observed,
                  observed_total: t.observed_total == null ? null : formatDec(t.observed_total, t.currency ?? undefined),
                  known_components: t.known_components == null ? null : formatDec(t.known_components, t.currency ?? undefined),
                  difference: t.difference == null ? null : formatDec(t.difference, t.currency ?? undefined),
                  tolerance: t.tolerance, flags: a.flags.length ? a.flags : '-',
                }} />
                {a.sub_portfolio_totals.length > 0 && (
                  <SimpleTable head={['Sub-portfolio', 'Observed', 'Known', 'Difference', 'Status']}
                    rows={a.sub_portfolio_totals.map((s) => [String(s.sub_portfolio), formatDec(s.observed_total as string), formatDec(s.known_components as string), formatDec(s.difference as string), <StatusBadge key="s" status={String(s.status)} />])} />
                )}
              </div>
            </details>
          );
        })}
      </div>
      {accounts.length === 0 && <p className="text-xs text-secondary">No account matches the filter.</p>}
      <div className="bg-surface border border-default rounded-lg p-4">
        <h3 className="text-sm font-semibold text-primary mb-2">Holdings identity</h3>
        <SimpleTable head={['Security', 'Type', 'Identity']}
          rows={securities.map((s) => [s.security_id, s.instrument_type ?? NOT_ESTABLISHED, <StatusBadge key="i" status={s.identity_status} />])} />
        <p className="text-[11px] text-muted mt-2">Values are in {ccy}. Holdings without owner-supplied identifiers are never merged across accounts.</p>
      </div>
    </div>
  );
};

const PortfolioReport: React.FC<{ view: UpiView; warnings: string[] }> = ({ view, warnings }) => {
  const meta = view.report_metadata;
  const ccy = meta.report_currency;
  const ov = view.portfolio_overview;
  const evidenceOnly = meta.report_type === 'EVIDENCE_ONLY_REPORT';
  const cap = view.financial_capacity;
  const reserve = cap.reserve;
  const conc = view.concentration;
  const findings = useMemo(() => findingsFor(warnings, view.decision_status.reasons), [warnings, view]);

  const statusCounts = view.accounts.reduce<Record<string, number>>((m, a) => ({ ...m, [a.account_total.status]: (m[a.account_total.status] ?? 0) + 1 }), {});
  const reconciled = (statusCounts.RECONCILED ?? 0) + (statusCounts.CONSISTENT_WITH_DISPLAY_ROUNDING ?? 0);
  const unexplained = statusCounts.UNEXPLAINED_DIFFERENCE ?? 0;
  const cash = view.allocation.computed_by_classification?.CASH;

  const composition: Segment[] = [
    { label: 'Computed NAV (PPDS)', value: evidenceOnly ? NOT_ESTABLISHED : formatDec(ov.computed_nav_ppds), fraction: barFraction(ov.computed_nav_ppds, ov.total_best_evidence), tone: 'accent' },
    { label: 'Observed value-only positions', value: formatDec(ov.observed_position_value), fraction: barFraction(ov.observed_position_value, ov.total_best_evidence), tone: 'sky' },
    { label: 'Unclassified holdings value', value: formatDec(ov.unclassified_holdings_value), fraction: barFraction(ov.unclassified_holdings_value, ov.total_best_evidence), tone: 'unknown', note: formatWeight(conc.unclassified_share) },
  ];
  const classification = view.allocation.computed_by_classification;
  const classSegments: Segment[] = classification
    ? Object.entries(classification).sort(([, a], [, b]) => byValueDesc(a.value, b.value))
        .map(([k, b]) => ({ label: humanize(k), value: formatDec(b.value), fraction: barFraction(b.weight), tone: classTone(k), note: formatWeight(b.weight) }))
    : [];

  const subEntries = Object.entries(view.allocation.by_sub_portfolio_best_evidence).sort(([, a], [, b]) => byValueDesc(a.value, b.value));
  const maxSub = subEntries[0]?.[1].weight;
  const subRows: BarRow[] = subEntries.map(([k, b]) => {
    const [account, bucket = ''] = k.split('/');
    const unclassified = bucket.includes('UNCLASSIFIED');
    const label = unclassified ? `${account} · unidentified holdings` : bucket === '(account cash)' ? `${account} · cash` : `${account} · ${bucket}`;
    return { key: k, label, value: formatDec(b.value), note: formatWeight(b.weight), fraction: barFraction(b.weight, maxSub), tone: unclassified ? 'unknown' : bucket === '(account cash)' ? 'emerald' : 'accent' };
  });
  const ccyEntries = Object.entries(view.allocation.currency_exposure_best_evidence).sort(([, a], [, b]) => byValueDesc(a.value, b.value));
  const ccyRows: BarRow[] = ccyEntries.map(([k, b]) => ({ key: k, label: k.includes('UNCLASSIFIED') ? 'Unidentified (currency unknown)' : k, value: formatDec(b.value), note: formatWeight(b.weight), fraction: barFraction(b.weight), tone: k.includes('UNCLASSIFIED') ? 'unknown' : 'sky' }));
  const topRows: BarRow[] = conc.top_holdings.map((h) => ({ key: h.key, label: h.key, value: formatWeight(h.weight), fraction: barFraction(h.weight), tone: 'violet' }));

  const scenarios = [...cap.scenarios].sort((a, b) => Number(a.monthly_contribution_thb) - Number(b.monthly_contribution_thb));
  const coverageRows: BarRow[] = Object.entries(view.coverage).filter(([, v]) => isDecimal(v)).map(([k, v]) => ({ key: k, label: humanize(k), value: formatWeight(v), fraction: barFraction(v), tone: 'accent' }));
  const coverageText = Object.entries(view.coverage).filter(([, v]) => !isDecimal(v));

  return (
    <div className="space-y-5">
      <GovernanceStrip view={view} />

      <section aria-labelledby="sec-a" className="space-y-3">
        <SectionHeader id="sec-a" letter="A" title="Executive overview" note="Total best evidence combines computed NAV, broker-displayed values and unidentified holdings. It is not a verified NAV. Broker totals are compared, never added." />
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          <SummaryCard label="Total best evidence" value={formatDec(ov.total_best_evidence)} unit={ccy} subtitle="Computed + observed value-only + unclassified. Not a verified NAV." />
          <SummaryCard label="Computed NAV (PPDS)" value={evidenceOnly ? NOT_ESTABLISHED : formatDec(ov.computed_nav_ppds)} unit={ccy}
            subtitle={evidenceOnly ? 'No cash or quantity line carries value in this report.' : 'Quantity × price + settled cash. A subset of the portfolio.'} />
          <SummaryCard label="Unclassified holdings" value={formatDec(ov.unclassified_holdings_value)} unit={ccy} tone={Number(ov.unclassified_holdings_value) > 0 ? 'warn' : 'default'}
            subtitle={`Broker totals minus identified lines · ${formatWeight(conc.unclassified_share)} of best evidence`} />
          <SummaryCard label="Cash (settled lines)" value={cash ? formatDec(cash.value) : NOT_ESTABLISHED} unit={ccy}
            subtitle="Settled cash lines in computed NAV. Cash inside broker totals is not separated." />
          <SummaryCard label="Emergency reserve" value={formatDec(reserve.current_thb)} unit="THB" tone={reserve.status === 'RESERVE_SHORTFALL' ? 'warn' : 'good'}
            badge={<StatusBadge status={reserve.status ?? 'NOT_ESTABLISHED'} />}
            subtitle={`Target ${formatDec(reserve.target_thb)} · shortfall ${formatDec(reserve.shortfall_thb)} · ${reserve.coverage_months ?? NOT_ESTABLISHED} months covered`} />
          <SummaryCard label="Account reconciliation" value={`${reconciled} / ${view.accounts.length}`} unit="reconciled" tone={unexplained > 0 ? 'bad' : reconciled === view.accounts.length ? 'good' : 'warn'}
            subtitle={Object.entries(statusCounts).map(([s, n]) => `${n} ${humanize(s).toLowerCase()}`).join(' · ')} />
        </div>
      </section>

      <section aria-labelledby="sec-f" className="space-y-3">
        <SectionHeader id="sec-f" letter="!" title="Findings" note="Grouped by a fixed rule: Critical = a figure may be wrong or out of date; Important = correct but incomplete, or a planning constraint; Info = not available in a snapshot report." />
        <Findings findings={findings} />
      </section>

      <section aria-labelledby="sec-b" className="space-y-3">
        <SectionHeader id="sec-b" letter="B" title="Portfolio allocation & exposure" note={`All weights come from the Python pack. Concentration status ${conc.status}: while unidentified value exists, weights are a lower bound, not portfolio-wide risk.`} />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
          <ChartCard title="Portfolio composition by evidence" subtitle={`Denominator: total best evidence (${formatDec(ov.total_best_evidence)} ${ccy}).`}
            table={<SimpleTable head={['Component', `Value (${ccy})`]} rows={composition.map((s) => [s.label, s.value])} />}>
            <StackedBar segments={composition} label="Portfolio composition" />
          </ChartCard>
          <ChartCard title="Asset class within computed NAV" subtitle="Denominator: computed NAV only. Value-only and unidentified holdings are not classified."
            table={classification ? <SimpleTable head={['Class', `Value (${ccy})`, 'Weight']} rows={classSegments.map((s) => [s.label, s.value, s.note])} /> : <StatusBadge status={view.allocation.computed_status} />}>
            {classification ? <StackedBar segments={classSegments} label="Classification within computed NAV" /> : <p className="text-xs text-secondary">{NOT_ESTABLISHED}: evidence-only report.</p>}
          </ChartCard>
          <ChartCard title="Sub-portfolios" subtitle="Sorted by value. Names are the owner's labels, not evidence-backed asset classes. Weights are of total best evidence."
            table={<SimpleTable head={['Bucket', `Value (${ccy})`, 'Weight']} rows={subRows.map((r) => [r.label, r.value, r.note])} />}>
            <BarList rows={subRows} label="Sub-portfolio values" />
          </ChartCard>
          <div className="space-y-3 min-w-0">
            <ChartCard title="Concentration" subtitle="Top identified holdings, weight of total best evidence."
              table={<SimpleTable head={['Holding', 'Weight']} rows={topRows.map((r) => [r.label, r.value])} />}>
              <div className="grid grid-cols-3 gap-2 text-center">
                {([['Top 1', formatWeight(conc.top1_weight)], ['HHI (identified)', conc.hhi_identified_securities ?? NOT_ESTABLISHED], ['Unidentified', formatWeight(conc.unclassified_share)]] as const).map(([k, v]) => (
                  <div key={k} className="bg-surface-muted rounded-md py-2"><div className="text-[10px] text-muted">{k}</div><div className="font-mono-code text-sm text-primary">{v}</div></div>
                ))}
              </div>
              {topRows.length ? <BarList rows={topRows} label="Top holdings" /> : <p className="text-xs text-secondary">{NOT_ESTABLISHED}</p>}
              <p className="text-[11px] text-muted">{conc.status === 'LOWER_BOUND_UNCLASSIFIED_VALUE_PRESENT' ? 'Lower bound: unidentified holdings may add to any of these.' : conc.status}</p>
            </ChartCard>
            <ChartCard title="Currency exposure" subtitle="Weight of total best evidence."
              table={<SimpleTable head={['Currency', `Value (${ccy})`, 'Weight']} rows={ccyRows.map((r) => [r.label, r.value, r.note])} />}>
              <BarList rows={ccyRows} label="Currency exposure" />
            </ChartCard>
          </div>
        </div>
      </section>

      <section aria-labelledby="sec-c" className="space-y-3">
        <SectionHeader id="sec-c" letter="C" title="Financial capacity" note="Planning scenarios computed by the Python capacity planner. Illustrative only: not advice and not an instruction to transfer money." />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
          <ChartCard title="Emergency reserve" subtitle={`Status ${reserve.status ?? NOT_ESTABLISHED}. Target from the expenses entered in capacity.`}
            table={<KeyValues values={reserve} />}>
            <StackedBar label="Emergency reserve versus target" segments={[
              { label: 'Current reserve', value: `${formatDec(reserve.current_thb)} THB`, fraction: barFraction(reserve.current_thb, reserve.target_thb), tone: 'emerald' },
              { label: 'Shortfall to target', value: `${formatDec(reserve.shortfall_thb)} THB`, fraction: barFraction(reserve.shortfall_thb, reserve.target_thb), tone: 'rose' },
            ]} />
            <p className="text-[11px] text-muted">Target {formatDec(reserve.target_thb)} THB · {reserve.coverage_months ?? NOT_ESTABLISHED} months of expenses covered.</p>
          </ChartCard>
          <ChartCard title="Monthly contribution scenarios" subtitle={`Monthly surplus ${formatDec(cap.monthly_surplus_thb)} THB (${cap.capacity_status}). Bar = surplus split into contribution and residual.`}
            table={<SimpleTable head={['Contribution (THB)', 'Residual', 'Months to reserve target', 'Status']}
              rows={scenarios.map((s) => [formatDec(s.monthly_contribution_thb), formatDec(s.residual_after_contribution_thb), s.months_to_reserve_target_from_residual ?? NOT_ESTABLISHED, <StatusBadge key="s" status={s.status} />])} />}>
            <ul className="space-y-3" aria-label="Contribution scenarios">
              {scenarios.map((s) => (
                <li key={s.monthly_contribution_thb} className="space-y-1">
                  <div className="flex items-baseline gap-2 text-xs">
                    <span className="text-primary font-mono-code">{formatDec(s.monthly_contribution_thb)} THB / month</span>
                    <span className="ml-auto text-secondary">residual <span className="font-mono-code text-primary">{formatDec(s.residual_after_contribution_thb)}</span></span>
                    <span className="text-muted w-28 text-right">{s.months_to_reserve_target_from_residual == null ? NOT_ESTABLISHED : `${s.months_to_reserve_target_from_residual} mo to target`}</span>
                  </div>
                  <div className="flex h-2.5 w-full rounded bg-surface-muted overflow-hidden" role="img"
                    aria-label={`Contribution ${s.monthly_contribution_thb}, residual ${s.residual_after_contribution_thb} THB`}>
                    <div className="bg-accent h-full" style={{ width: `${barFraction(s.monthly_contribution_thb, cap.monthly_surplus_thb) * 100}%` }} />
                    <div className="bg-emerald-500 h-full" style={{ width: `${barFraction(s.residual_after_contribution_thb, cap.monthly_surplus_thb) * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
            <div className="flex gap-4 text-[11px] text-muted"><span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-accent" />Contribution</span><span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-emerald-500" />Residual for reserve</span></div>
          </ChartCard>
        </div>
        <Disclosure title="Hypothetical quant research budget (not authorized, never funded from the reserve)">
          <KeyValues values={cap.quant_budget} />
        </Disclosure>
      </section>

      <section aria-labelledby="sec-d" className="space-y-3">
        <SectionHeader id="sec-d" letter="D" title="Accounts & holdings" note="One card per observed account; open a card for totals, differences and sub-portfolio checks." />
        <AccountsAndHoldings view={view} ccy={ccy} />
      </section>

      <section aria-labelledby="sec-e" className="space-y-3">
        <SectionHeader id="sec-e" letter="E" title="Evidence & governance" note="Data quality is about the evidence, not investment performance." />
        <ChartCard title="Data coverage" subtitle="Share of total best evidence backed by each kind of evidence."
          table={<KeyValues values={view.coverage} />}>
          <BarList rows={coverageRows} label="Data coverage" />
          {coverageText.length > 0 && <KeyValues values={Object.fromEntries(coverageText)} />}
        </ChartCard>
        <Disclosure title="Report metadata and decision">
          <div className="flex items-center gap-2">
            <StatusBadge status={view.decision_status.conclusion} size="md" />
            <span className="text-xs text-secondary font-mono-code">orders generated: {view.decision_status.orders_generated}</span>
          </div>
          <KeyValues values={{
            report_type: meta.report_type, valuation_date: meta.valuation_date, observed_at: meta.observed_at,
            observation_lag_days: meta.observation_lag_days, valuation_age_days: meta.valuation_age_days,
            valuation_stale: meta.valuation_stale, support_state: meta.support_state,
            performance: view.data_quality.performance_status, market_session: view.data_quality.market_session_status,
            unsupported_analyses: meta.unsupported_analyses.length ? meta.unsupported_analyses : '-',
          }} />
        </Disclosure>
        <Disclosure title="Observation authority, governance flags and quant workspace">
          <KeyValues values={view.governance.observation_authority} />
          <KeyValues values={view.governance.flags} />
          <KeyValues values={view.quant_workspace} />
        </Disclosure>
        <Disclosure title="Provenance">
          <KeyValues values={{ pack_version: meta.pack_version, pack_sha256: meta.pack_sha256, view_sha256: view.view_sha256,
            snapshot_id: meta.snapshot_id, snapshot_schema: meta.snapshot_schema }} />
        </Disclosure>
      </section>
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
      <div className="bg-surface border border-default rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold text-primary">Portfolio Intelligence</h1>
            <p className="text-xs text-secondary">Read-only view of the Python wealth pack. Figures are computed in Python; this page only displays them.</p>
          </div>
          <div className="flex gap-1 p-1 bg-surface-muted rounded-md" role="group" aria-label="Data mode">
            {(['SYNTHETIC_DEMO', 'OWNER_PRIVATE_READ_ONLY'] as DataMode[]).map((m) => (
              <button key={m} onClick={() => switchMode(m)} aria-pressed={mode === m}
                className={`text-xs px-3 py-1.5 rounded font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${mode === m ? 'bg-accent text-white shadow-sm' : 'text-secondary hover:text-primary'}`}>
                {m === 'SYNTHETIC_DEMO' ? 'Synthetic demo' : 'Owner private'}
              </button>
            ))}
          </div>
        </div>
        {mode === 'SYNTHETIC_DEMO' ? (
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <StatusBadge status="DEMO_DATA" size="md" />
            <span className="text-secondary">Public synthetic fixture · not owner data</span>
            <select value={variant} onChange={(e) => setVariant(e.target.value as SyntheticVariant)} aria-label="Synthetic report"
              className="ml-auto text-xs bg-surface border border-default rounded px-2 py-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent">
              <option value="FULL_REPORT">Full report fixture</option>
              <option value="EVIDENCE_ONLY_REPORT">Evidence-only fixture</option>
            </select>
          </div>
        ) : (
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2 text-secondary">
              <Lock className="w-3.5 h-3.5" />
              <span>Owner private · read-only · loopback only. Requires ODR-001 RATIFIED. Start with <code className="font-mono-code">START-DASHBOARD.bat private</code>, then paste the token from the "ACASH Private View" window.</span>
            </div>
            <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); void connect(); }}>
              <input type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); if (e.currentTarget.value && !loading) void connect(e.currentTarget.value); } }}
                placeholder="Session token printed by the local service" aria-label="Session token"
                className="flex-1 min-w-[16rem] bg-surface border border-default rounded px-2 py-1 font-mono-code focus:outline-none focus-visible:ring-2 focus-visible:ring-accent" />
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
              <span className="text-secondary">{state.warnings.length} findings below</span>
            )}
          </div>
        )}
      </div>

      {loading && <SkeletonLoader className="h-40 w-full" />}
      {!loading && state && 'view' in state && <PortfolioReport view={state.view} warnings={state.warnings} />}
      {!loading && state && !('view' in state) && (
        <div className="bg-surface border border-default rounded-lg p-6 flex items-start gap-3 text-sm">
          <ShieldAlert className="w-5 h-5 text-muted shrink-0" />
          <div className="space-y-1">
            <div className="font-semibold text-primary">{state.status.replace(/_/g, ' ')}</div>
            <div className="text-xs text-secondary">{STATUS_HELP[state.status]}</div>
            <div className="text-xs text-secondary">No figures are shown. Synthetic data is never substituted for owner data.</div>
          </div>
        </div>
      )}
      {!loading && !state && mode === 'OWNER_PRIVATE_READ_ONLY' && (
        <div className="bg-surface border border-default rounded-lg p-6 text-xs text-secondary">
          AUTHORIZATION REQUIRED · enter the session token from the local service to load the owner-private view.
        </div>
      )}
    </div>
  );
};
