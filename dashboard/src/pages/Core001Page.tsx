/**
 * ACASH CORE-001 / HYP_011 — Read-Only Observability Page
 *
 * Strictly presentational. No buttons that mutate anything: no BUY/SELL,
 * no Run Observation, no paper/live authorization, no backfill.
 * Pre-first-observation renders PRE-S1 with N/A states (never ERROR).
 */

import React, { useEffect, useState } from 'react';
import { Core001ApiResponse, Core001DashboardState } from '../types/core001';
import { core001Repository } from '../services/core001Repository';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';
import { SkeletonLoader } from '../components/common/SkeletonLoader';
import { EquityDrawdownChart } from '../components/charts/EquityDrawdownChart';
import { EquityPoint } from '../types/research';

function fmtMoney(value: string | null): string {
  if (value === null || value === undefined) return 'N/A';
  const n = Number(value);
  if (!Number.isFinite(n)) return 'N/A';
  return `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtPct(value: string | null): string {
  if (value === null || value === undefined) return 'N/A';
  const n = Number(value);
  if (!Number.isFinite(n)) return 'N/A';
  return `${(n * 100).toFixed(2)}%`;
}

function toChartPoints(state: Core001DashboardState): EquityPoint[] {
  return state.equity_series.map((p, i) => {
    const equity = Number(p.strategy_equity);
    const dd = Number(p.strategy_drawdown) * 100;
    return {
      index: i,
      date: p.session,
      timestamp: p.session,
      equity,
      drawdownPct: Number.isFinite(dd) ? dd : 0,
      grossEquity: equity,
      netEquity: equity,
      cash: 0,
      tradeCount: 0,
    };
  });
}

export const Core001Page: React.FC = () => {
  const [response, setResponse] = useState<Core001ApiResponse | null>(null);

  useEffect(() => {
    const unsubscribe = core001Repository.subscribe(setResponse);
    return unsubscribe;
  }, []);

  if (!response || !response.data) {
    return (
      <div className="p-8 flex flex-col space-y-4 max-w-6xl mx-auto">
        <SkeletonLoader className="h-10 w-full" />
        <SkeletonLoader className="h-16 w-full" />
      </div>
    );
  }

  const s = response.data;
  const chartData = toChartPoints(s);
  const blocked = s.evidence.status === 'EVIDENCE_INVALID_OR_BLOCKED';

  if (blocked) {
    return (
      <div className="p-6 max-w-6xl mx-auto space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold text-primary">ACASH CORE-001</h1>
          <StatusBadge status="EVIDENCE_INVALID_OR_BLOCKED" size="md" />
        </div>
        <div className="bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 rounded-md p-4 text-xs">
          <p className="font-semibold text-rose-800 dark:text-rose-300 mb-1">Evidence unreadable — fail-closed. No state was assumed healthy.</p>
          <p className="font-mono-code text-rose-800 dark:text-rose-300">Reason: {s.evidence.reason}</p>
        </div>
        <div className="flex flex-wrap gap-2 items-center text-xs">
          <span className="text-secondary">Paper:</span>
          <StatusBadge status="NOT_AUTHORIZED" />
          <span className="text-secondary ml-2">Live:</span>
          <StatusBadge status="LOCKED" />
          <span className="text-secondary ml-2">Real Capital:</span>
          <span className="font-mono-code text-primary">$0.00</span>
          <span className="text-secondary ml-2">NO_REAL_ORDERS:</span>
          <StatusBadge status="TRUE" />
        </div>
        <p className="text-[11px] text-muted font-mono-code">
          READ-ONLY OBSERVABILITY — corruption is surfaced, never converted into a healthy-looking empty state.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <h1 className="text-xl font-semibold text-primary">ACASH CORE-001</h1>
          <p className="text-xs text-secondary font-mono-code">
            {s.identity.hypothesis_id} · {s.identity.strategy_name}
          </p>
        </div>
        <StatusBadge status={s.governance.stage} size="md" />
        <StatusBadge status={s.dataSource === 'SNAPSHOT' ? 'SEALED_SNAPSHOT' : 'AWAITING_OBSERVATION'} size="md" />
      </div>

      {/* Authority strip */}
      <div className="flex flex-wrap gap-2 items-center text-xs">
        <span className="text-secondary">Paper:</span>
        <StatusBadge status={s.governance.paper_authorized ? 'AUTHORIZED' : 'NOT_AUTHORIZED'} />
        <span className="text-secondary ml-2">Live:</span>
        <StatusBadge status={s.governance.live_authorized ? 'AUTHORIZED' : 'LOCKED'} />
        <span className="text-secondary ml-2">Real Capital:</span>
        <span className="font-mono-code text-primary">$0.00</span>
        <span className="text-secondary ml-2">NO_REAL_ORDERS:</span>
        <StatusBadge status={s.governance.no_real_orders ? 'TRUE' : 'FALSE'} />
        <span className="text-secondary ml-2">Shadow Simulated Equity (not real capital)</span>
      </div>

      {/* Evidence progress */}
      <section>
        <h2 className="text-sm font-semibold text-primary mb-2">Evidence Progress</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard label="S1 Operational Sanity" value={`${Math.min(s.progress.observed_sessions, 20)} / 20`} subValue="actually observed sessions" />
          <MetricCard label="S2 Short Qualification" value={`${Math.min(s.progress.observed_sessions, 60)} / 60`} subValue="Obs 1–60 window" />
          <MetricCard label="Long Horizon" value={`${Math.min(s.progress.observed_sessions, 504)} / 504`} subValue="high-confidence confirmation" />
          <MetricCard
            label="Annual Rebalances"
            value={`${s.progress.completed_annual_rebalances} / ${s.progress.required_annual_rebalances}`}
            subValue="scheduled only"
          />
        </div>
      </section>

      {/* Portfolio */}
      <section>
        <h2 className="text-sm font-semibold text-primary mb-2">Portfolio — {s.portfolio.basis.replace(/_/g, ' ')}</h2>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <MetricCard label="Shadow Simulated Equity" value={fmtMoney(s.portfolio.total_equity)} />
          <MetricCard label="Cash" value={fmtMoney(s.portfolio.cash)} />
          <MetricCard label="Receivable" value={fmtMoney(s.portfolio.receivable)} />
          <MetricCard label="ACWI shares" value={String(s.portfolio.holdings['ACWI'] ?? 'N/A')} />
          <MetricCard label="AGG shares" value={String(s.portfolio.holdings['AGG'] ?? 'N/A')} />
        </div>
      </section>

      {/* S2 guardrails */}
      <section>
        <h2 className="text-sm font-semibold text-primary mb-2">S2 Safety Guardrails</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <MetricCard
            label="MDD (PASS < 25%)"
            value={fmtPct(s.s2.current_mdd)}
            subValue="current 60-session window"
            badge={<StatusBadge status={s.s2.evaluation_state} />}
          />
          <MetricCard
            label="60-session Return (PASS > -20%)"
            value={fmtPct(s.s2.current_cumulative_return)}
            subValue="diagnostic only until Observation 60"
            badge={<StatusBadge status={s.s2.evaluation_state} />}
          />
          <MetricCard
            label="Worst Daily (PASS > -10%)"
            value={fmtPct(s.s2.worst_daily_return)}
            subValue="any breach blocks pending human review"
            badge={<StatusBadge status={s.s2.evaluation_state} />}
          />
        </div>
      </section>

      {/* Equity chart */}
      <section>
        <h2 className="text-sm font-semibold text-primary mb-2">Shadow Simulated Equity & Drawdown</h2>
        {chartData.length === 0 ? (
          <EmptyState
            title="No observations yet"
            message="Observation #0001 has not been sealed. The equity curve will appear here once the first sealed observation exists. Missed sessions are never backfilled."
          />
        ) : (
          <EquityDrawdownChart data={chartData} />
        )}
      </section>

      {/* Evidence */}
      <section>
        <h2 className="text-sm font-semibold text-primary mb-2">Evidence</h2>
        <div className="bg-surface border border-default rounded-md p-4 text-xs font-mono-code space-y-1.5">
          <div className="flex justify-between"><span className="text-secondary">Last Observation</span><span className="text-primary">{s.evidence.latest_observation_session ?? 'NONE'}</span></div>
          <div className="flex justify-between"><span className="text-secondary">Ordinal</span><span className="text-primary">{s.evidence.latest_observation_ordinal ?? 'NONE'}</span></div>
          <div className="flex justify-between"><span className="text-secondary">Status</span><span className="text-primary">{s.evidence.status.replace(/_/g, ' ')}</span></div>
          <div className="flex justify-between"><span className="text-secondary">Artifact SHA256</span><span className="text-primary truncate max-w-[60%]" title={s.evidence.latest_artifact_sha256 ?? ''}>{s.evidence.latest_artifact_sha256 ?? 'N/A'}</span></div>
          <div className="flex justify-between"><span className="text-secondary">Previous SHA256</span><span className="text-primary truncate max-w-[60%]" title={s.evidence.previous_artifact_sha256 ?? ''}>{s.evidence.previous_artifact_sha256 ?? 'N/A'}</span></div>
          <div className="flex justify-between"><span className="text-secondary">State Chain</span><span className="text-primary">{s.evidence.state_chain_health ?? 'N/A'}</span></div>
          <div className="flex justify-between"><span className="text-secondary">Corporate Action</span><span className="text-primary">{s.evidence.corporate_action_status ?? 'N/A'}</span></div>
          <div className="flex justify-between"><span className="text-secondary">Last Incident</span><span className="text-primary">{s.incident.category} ({s.incident.basis.replace(/_/g, ' ')})</span></div>
          <div className="flex justify-between"><span className="text-secondary">Timer / Service</span><span className="text-primary">UNAVAILABLE FROM DASHBOARD</span></div>
        </div>
      </section>

      <p className="text-[11px] text-muted font-mono-code">
        READ-ONLY OBSERVABILITY — this page reads sealed evidence and derives presentation. It cannot observe,
        authorize, execute, or mutate anything. CURRENT FACT labels mark sealed evidence; DIAGNOSTIC marks
        non-decisive values; LOCKED / UNAUTHORIZED mark authority boundaries.
      </p>
    </div>
  );
};

export default Core001Page;
