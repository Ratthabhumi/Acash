import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { SimpleTable } from '../charts/PortfolioCharts';
import { callMarket } from '../../services/marketRefresh';
import { marketSession } from '../../services/marketSession';

// Displays the *derived* research output written by scripts/backfill_massive_universe.py plus the
// collector's own health record. It shows what Python computed and nothing else: no price is read in
// the browser, no weight is recalculated here, and there is no order control anywhere in this view.

interface CoverageRow {
  sessions: number; first?: string; last?: string; status: string;
  missing_vs_union?: number; error?: string | null;
}

interface ResearchDoc {
  status: string;
  generated_at?: string;
  coverage?: { union_sessions?: number; union_first?: string; union_last?: string;
    covered?: number; partial?: number; missing?: number };
  symbols?: Record<string, CoverageRow>;
  universe?: { requested?: number; eligible?: string[]; excluded?: Record<string, { reason: string; sessions: number }> };
  panel_sessions?: number;
  panel_range?: { first?: string; last?: string };
  proposal?: Record<string, unknown>;
  requests?: number;
  storage_rights?: string;
  governance?: Record<string, unknown>;
  collector_health?: Record<string, unknown>;
  note?: string;
}

const str = (value: unknown): string => (value === null || value === undefined ? '—' : String(value));

const SessionCard: React.FC = () => {
  const [view, setView] = useState(() => marketSession());
  useEffect(() => {
    const timer = window.setInterval(() => setView(marketSession()), 60000);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <div className="bg-surface border border-default rounded-lg p-3 space-y-1 text-xs">
      <div className="flex items-center gap-2">
        <StatusBadge status={view.state === 'OPEN' ? 'MARKET_OPEN' : 'MARKET_CLOSED'} />
        <span className="text-secondary">New York {view.new_york_time} · Bangkok {view.bangkok_time}</span>
      </div>
      {view.next_change && (
        <p className="text-secondary">
          ถัดไป: {view.next_change.kind === 'OPEN' ? 'เปิดตลาด' : 'ปิดตลาด'} · {view.next_change.at_bangkok}
          <span className="text-muted"> (ET {view.next_change.at_ny})</span>
        </p>
      )}
      <p className="text-[11px] text-muted">
        ตารางวันหยุดตลาดสหรัฐยังไม่ได้ยืนยัน (ไม่มีปฏิทินที่ผ่านการตรวจ) จึงไม่แสดงว่าวันนี้เป็นวันหยุด
      </p>
    </div>
  );
};

export const ResearchDecisionPanel: React.FC = () => {
  const [doc, setDoc] = useState<ResearchDoc | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const response = await callMarket<ResearchDoc>('GET', 'research');
    setDoc(response.body as ResearchDoc);
    setLoading(false);
  }, []);

  useEffect(() => { void load(); }, [load]);

  const proposal = (doc?.proposal ?? {}) as Record<string, unknown>;
  const coverage = doc?.coverage ?? {};
  const excluded = doc?.universe?.excluded ?? {};
  const eligible = doc?.universe?.eligible ?? [];
  const symbols = doc?.symbols ?? {};
  const actions = (proposal.proposed_actions as Array<Record<string, string>> | undefined) ?? [];
  const risk = (proposal.modeled_risk ?? {}) as Record<string, unknown>;
  const target = (proposal.target_weights ?? {}) as Record<string, string>;
  const limitations = (proposal.limitations as string[] | undefined) ?? [];
  const missing = (proposal.missing_evidence as string[] | undefined) ?? [];
  const strategies = (proposal.evaluated_strategies as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <section aria-labelledby="sec-research" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id="sec-research" className="text-sm font-semibold text-primary">
          Historical data &amp; research decision
        </h3>
        <div className="flex items-center gap-2 text-xs">
          <button type="button" onClick={() => void load()} disabled={loading}
            className="inline-flex items-center gap-1 px-3 py-1 rounded border border-default text-secondary hover:bg-surface-muted disabled:opacity-50">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Reload
          </button>
          <StatusBadge status={str(doc?.status ?? 'LOADING')} size="md" />
        </div>
      </div>

      <SessionCard />

      {!loading && doc && doc.status === 'NO_RESEARCH_RUN' && (
        <div className="bg-surface border border-default rounded-lg p-4 text-xs text-secondary space-y-1">
          <p className="font-semibold text-primary">ยังไม่มีผลการดึงข้อมูลย้อนหลัง</p>
          <p>{doc.note}</p>
          <p>ไม่มีตัวเลขใดถูกสร้างขึ้นแทนข้อมูลจริง</p>
        </div>
      )}

      {!loading && doc && doc.status !== 'NO_RESEARCH_RUN' && (
        <>
          <div className="bg-surface border border-default rounded-lg p-3 text-xs space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={str(proposal.recommendation_status ?? 'INCOMPLETE_EVIDENCE')} />
              <span className="font-mono-code text-secondary">strategy: {str(proposal.strategy_id)}</span>
              <span className="text-muted">execution authority: {str(proposal.execution_authority ?? 'NONE')}</span>
            </div>
            <p className="text-secondary">
              ผลวิจัยนี้ไม่ใช่คำสั่งซื้อและไม่ใช่การรับรองผลตอบแทน · {' '}
              {eligible.length}/{str(doc.universe?.requested)} instruments มีประวัติเพียงพอ ·
              panel {str(doc.panel_sessions)} sessions ({str(doc.panel_range?.first)} → {str(doc.panel_range?.last)})
            </p>
            <p className="text-muted">
              requests {str(doc.requests)} · storage rights {str(doc.storage_rights)} ·
              generated {str(doc.generated_at)}
            </p>
          </div>

          <SimpleTable
            head={['Item', 'Value']}
            rows={[
              ['Sessions covered / partial / missing',
                `${str(coverage.covered)} / ${str(coverage.partial)} / ${str(coverage.missing)}`],
              ['Union sessions', `${str(coverage.union_sessions)} (${str(coverage.union_first)} → ${str(coverage.union_last)})`],
              ['In-sample / out-of-sample periods',
                `${str((proposal.in_sample_period as Record<string, unknown> | undefined)?.periods)} / ${str((proposal.out_of_sample_period as Record<string, unknown> | undefined)?.periods)}`],
              ['Cash weight', str(proposal.cash_weight)],
              ['OOS Sharpe (modelled)', str(risk.oos_sharpe)],
              ['OOS CVaR 95% (modelled)', str(risk.oos_cvar_95)],
              ['Constraints satisfied', str(risk.constraints_satisfied)],
              ['Hurdle cleared', str(risk.hurdle_rate_cleared)],
              ['Costs', `${str(proposal.transaction_cost_status)} · ${str(proposal.modeled_transaction_cost)}`],
              ['Turnover', str(proposal.turnover_required)],
            ]}
          />

          {actions.length > 0 && (
            <SimpleTable head={['Action', 'Instrument', 'Current', 'Target']}
              rows={actions.map((a) => [a.action, a.symbol, str(a.current_weight), str(a.target_weight)])} />
          )}

          {strategies.length > 0 && (
            <SimpleTable head={['Strategy', 'Rank score', 'Constraints', 'Hurdle']}
              rows={strategies.map((s) => [str(s.strategy), str(s.rank_score), str(s.constraints_satisfied),
                str(s.hurdle_rate_cleared)])} />
          )}

          <details className="bg-surface border border-default rounded-lg p-3 text-xs">
            <summary className="cursor-pointer font-semibold text-primary">Target weights &amp; rank scores</summary>
            <div className="mt-2 space-y-2">
              <SimpleTable head={['Instrument', 'Target weight']}
                rows={Object.entries(target).map(([k, v]) => [k, v])} />
              <SimpleTable head={['Strategy', 'Rank score']}
                rows={Object.entries((proposal.rank_scores ?? {}) as Record<string, string>).map(([k, v]) => [k, v])} />
              <p className="text-[11px] text-muted">Rank score ไม่ใช่เปอร์เซ็นต์ผลตอบแทน</p>
            </div>
          </details>

          <details className="bg-surface border border-default rounded-lg p-3 text-xs">
            <summary className="cursor-pointer font-semibold text-primary">Coverage per instrument</summary>
            <div className="mt-2">
              <SimpleTable head={['Instrument', 'Sessions', 'First', 'Last', 'Missing', 'Status']}
                rows={Object.entries(symbols).map(([symbol, row]) => [
                  symbol, str(row.sessions), str(row.first), str(row.last), str(row.missing_vs_union),
                  row.error ? `${row.status}: ${row.error}` : row.status,
                ])} />
            </div>
          </details>

          {Object.keys(excluded).length > 0 && (
            <div className="bg-surface border border-default rounded-lg p-3 text-xs space-y-1">
              <p className="font-semibold text-primary">Excluded from the research universe</p>
              <SimpleTable head={['Instrument', 'Reason', 'Sessions']}
                rows={Object.entries(excluded).map(([symbol, row]) => [symbol, row.reason, str(row.sessions)])} />
              <p className="text-muted">
                หลักทรัพย์ที่ถูกตัดออกยังคงอยู่ในพอร์ตจริงและยังมีความเสี่ยงจริง · ผลวิจัยนี้จึงไม่ครอบคลุมทั้งพอร์ต
              </p>
            </div>
          )}

          {(limitations.length > 0 || missing.length > 0) && (
            <div className="bg-surface border border-default rounded-lg p-3 text-xs space-y-1">
              <p className="font-semibold text-primary">Limitations</p>
              <ul className="list-disc pl-5 text-secondary">
                {limitations.map((item) => <li key={item}>{item}</li>)}
              </ul>
              {missing.length > 0 && (
                <p className="text-muted">Missing evidence: {missing.join(' · ')}</p>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
};
