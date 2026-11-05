import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { SimpleTable } from '../charts/PortfolioCharts';
import { callMarket } from '../../services/marketRefresh';

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
  fx?: Record<string, unknown>;
  universe_status?: string;
  evidence_labels?: string[];
  cohorts?: Array<Record<string, unknown>>;
  performance_basis?: string;
  realized_performance?: boolean;
  note?: string;
}

const str = (value: unknown): string => (value === null || value === undefined ? '—' : String(value));

interface SessionDoc {
  state?: string;
  mic?: string;
  calendar_status?: string;
  regular?: { open_et?: string; close_et?: string; early_close_et?: string };
  today?: { date?: string; status?: string; open_ict?: string | null; close_ict?: string | null };
  next_session?: { date?: string; status?: string; open_ict?: string; close_ict?: string } | null;
  eod_eligible_after?: string | null;
  observed_at?: { et?: string; ict?: string };
  source?: Record<string, string>;
}

const SessionCard: React.FC<{ session: SessionDoc | null }> = ({ session }) => {
  if (!session) {
    return (
      <div className="bg-surface border border-default rounded-lg p-3 text-xs text-secondary">
        ยังโหลดปฏิทินตลาดไม่ได้ — ไม่แสดงเวลาเปิด/ปิดแบบคาดเดา
      </div>
    );
  }
  const verified = session.calendar_status === 'VERIFIED_VENUE_FIXTURE';
  return (
    <div className="bg-surface border border-default rounded-lg p-3 space-y-1 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={session.state ?? 'UNKNOWN'} />
        <span className="font-mono-code text-secondary">{session.mic ?? 'VENUE_UNKNOWN'}</span>
        <span className="text-muted">{verified ? 'ปฏิทินผ่านการตรวจ (fixture)' : session.calendar_status}</span>
      </div>
      <p className="text-secondary">
        วันนี้ {session.today?.date ?? '—'} · {session.today?.status ?? '—'}
        {session.today?.open_ict ? ` · เปิด ${session.today.open_ict}` : ''}
        {session.today?.close_ict ? ` · ปิด ${session.today.close_ict}` : ''}
      </p>
      {session.next_session && (
        <p className="text-secondary">
          session ถัดไป: {session.next_session.date} ({session.next_session.status}) · เปิด {session.next_session.open_ict} · ปิด {session.next_session.close_ict}
        </p>
      )}
      {session.eod_eligible_after && (
        <p className="text-muted">ข้อมูล EOD ของวันนี้ควรพร้อมหลัง {session.eod_eligible_after}</p>
      )}
      <p className="text-[11px] text-muted">
        เวลาแปลงจาก America/New_York เป็น Asia/Bangkok ตาม timezone จริง (รองรับ DST และ early close) ·
        ปฏิทินไทยไม่เกี่ยวกับตลาดสหรัฐ
      </p>
    </div>
  );
};

interface FxDoc {
  status?: string;
  source?: string;
  rate_type?: string;
  orientation?: string;
  executable?: boolean;
  first?: string;
  last?: string;
  points?: number;
  weekday_gaps?: number;
  latest?: { date?: string; usd_thb?: string; retrieved_at?: string };
  decomposition?: {
    sessions?: number;
    first?: string;
    last?: string;
    portfolio?: { usd_price_return?: string; fx_translation?: string; thb_return?: string;
      cross_term?: string; weight_basis?: string };
    caveats?: string[];
  };
}

const FxCard: React.FC<{ fx: FxDoc | null }> = ({ fx }) => {
  if (!fx || fx.status === 'NO_FX_SERIES') {
    return (
      <div className="bg-surface border border-default rounded-lg p-3 text-xs text-secondary">
        ยังไม่มีชุดข้อมูล FX อ้างอิง (BOT) — ยังไม่คำนวณผลตอบแทนเป็นเงินบาท
      </div>
    );
  }
  const d = fx.decomposition?.portfolio;
  const pct = (value?: string) => (value === undefined ? '—' : `${(Number(value) * 100).toFixed(2)}%`);
  return (
    <div className="bg-surface border border-default rounded-lg p-3 space-y-1 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={fx.status ?? 'UNKNOWN'} />
        <span className="font-mono-code text-primary">
          {fx.latest?.usd_thb ?? '—'} THB/USD
        </span>
        <span className="text-muted">{fx.latest?.date ?? '—'} · {fx.source ?? '—'}</span>
      </div>
      <p className="text-[11px] text-secondary">
        {fx.rate_type ?? '—'} · {fx.orientation ?? '—'} · ใช้ซื้อขายจริงไม่ได้ ({fx.executable ? 'ไม่' : 'ถูกต้อง: reference only'})
      </p>
      <p className="text-secondary">
        ชุดข้อมูล {fx.points ?? 0} วัน ({fx.first} → {fx.last}) · ช่องว่างวันธรรมดา {fx.weekday_gaps ?? 0} วัน
        (ไม่เติมค่า)
      </p>
      {d && (
        <div className="pt-1">
          <p className="text-secondary">
            ผลตอบแทนพอร์ตช่วง {fx.decomposition?.first} → {fx.decomposition?.last} ({fx.decomposition?.sessions} sessions):
          </p>
          <ul className="list-disc pl-5 text-secondary">
            <li>ราคา USD: {pct(d.usd_price_return)}</li>
            <li>ค่าเงิน (FX translation): {pct(d.fx_translation)}</li>
            <li>Cross term: {pct(d.cross_term)}</li>
            <li>รวมเป็นเงินบาท: {pct(d.thb_return)}</li>
          </ul>
          <p className="text-[11px] text-muted">
            (1 + R_THB) = (1 + R_USD)(1 + R_FX) · น้ำหนัก {d.weight_basis ?? '—'} · เป็นการประมาณการ ไม่ใช่กำไรจริง
          </p>
        </div>
      )}
    </div>
  );
};

interface ProvidersDoc {
  providers?: Array<{ provider_id: string; status: string; detail?: string }>;
}

const labelText = (label: string): string => ({
  HYPOTHETICAL_HISTORICAL_BASKET: 'การจำลองตะกร้าย้อนหลัง (ไม่ใช่พอร์ตจริงในอดีต)',
  PRICE_RETURN_ONLY: 'ใช้ราคาอย่างเดียว ไม่รวมเงินปันผล',
  CURRENT_WEIGHTS_APPLIED_HISTORICALLY: 'ใช้น้ำหนักปัจจุบันย้อนหลัง',
  NOT_TRANSACTION_RECONSTRUCTED: 'ไม่ได้สร้างจากประวัติซื้อขายจริง',
  NOT_REALIZED_PORTFOLIO_PERFORMANCE: 'ไม่ใช่ผลตอบแทนที่เกิดขึ้นจริง',
  BOT_REFERENCE_FX_NOT_EXECUTABLE: 'FX อ้างอิง ใช้ซื้อขายจริงไม่ได้',
  PARTIAL_UNIVERSE_RESEARCH: 'วิเคราะห์บางส่วนของพอร์ต',
  FULL_UNIVERSE_QUALIFIED: 'ครบทั้งพอร์ตที่ผ่านเกณฑ์',
  EXECUTION_AUTHORITY_NONE: 'ไม่มีสิทธิ์สั่งซื้อขาย',
}[label] ?? label);

const ProviderHealthCard: React.FC<{ providers: ProvidersDoc | null; fx: FxDoc | null;
  coverageLast: string | null; partitions: number | null }> = ({ providers, fx, coverageLast, partitions }) => {
  const find = (id: string) => providers?.providers?.find((p) => p.provider_id === id);
  const rows: Array<[string, string]> = [
    ['Massive (price history)', `${find('MASSIVE_BASIC')?.status ?? 'UNKNOWN'} · session ล่าสุด ${coverageLast ?? '—'} · ${partitions ?? 0} partitions`],
    ['BOT FX (reference)', `${find('BOT_REFERENCE_FX')?.status ?? 'UNKNOWN'} · ${fx?.latest?.usd_thb ?? '—'} THB/USD (${fx?.latest?.date ?? '—'})`],
    ['BOT Holidays (Thai calendar)', `${find('BOT_HOLIDAYS')?.status ?? 'UNKNOWN'} · ใช้กับงานธนาคารไทยเท่านั้น ไม่ใช้แทนตลาดสหรัฐ`],
    ['Twelve Data (cross-check)', `${find('TWELVE_DATA_BASIC')?.status ?? 'UNKNOWN'} · key มีแล้ว แต่ adapter/สิทธิ์ข้อมูลยังไม่ยืนยัน → ปิดใช้`],
    ['Alpha Vantage (cross-check)', `${find('ALPHA_VANTAGE_FREE')?.status ?? 'UNKNOWN'} · งบ 3 คำขอ/วัน เมื่อเปิดใช้ (ยังปิด)`],
    ['Collector (Homelab)', 'NOT_DEPLOYED · รอติดตั้ง Ubuntu ใหม่ (Windows เก็บข้อมูลอยู่)'],
  ];
  return (
    <div className="bg-surface border border-default rounded-lg p-3 text-xs space-y-1">
      <p className="font-semibold text-primary">Provider health</p>
      <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1">
        {rows.map(([k, v]) => (
          <div key={k}>
            <dt className="text-muted">{k}</dt>
            <dd className="font-mono-code text-primary break-words">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
};

export const ResearchDecisionPanel: React.FC = () => {
  const [doc, setDoc] = useState<ResearchDoc | null>(null);
  const [session, setSession] = useState<SessionDoc | null>(null);
  const [providers, setProviders] = useState<ProvidersDoc | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const [response, calendar, status] = await Promise.all([
      callMarket<ResearchDoc>('GET', 'research'),
      callMarket<SessionDoc>('GET', 'session'),
      callMarket<ProvidersDoc>('GET', 'status'),
    ]);
    setDoc(response.body as ResearchDoc);
    setSession(calendar.body as SessionDoc);
    setProviders(status.body as ProvidersDoc);
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <SessionCard session={session} />
        <FxCard fx={(doc?.fx as FxDoc | undefined) ?? null} />
      </div>

      <ProviderHealthCard providers={providers} fx={(doc?.fx as FxDoc | undefined) ?? null}
        coverageLast={coverage.union_last ?? null}
        partitions={Number((doc?.collector_health as Record<string, unknown> | undefined)?.partitions_present ?? 0) || null} />

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
            {(doc.evidence_labels ?? []).length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                {(doc.evidence_labels ?? []).map((label) => (
                  <span key={label} title={label}
                    className="text-[10px] px-1.5 py-0.5 rounded border border-default bg-surface-muted text-secondary">
                    {labelText(label)}
                  </span>
                ))}
              </div>
            )}
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

          {(doc.cohorts ?? []).length > 0 && (
            <div className="bg-surface border border-default rounded-lg p-3 space-y-1 text-xs">
              <p className="font-semibold text-primary">Research cohorts (แยกช่วงเวลา ห้ามเทียบคะแนนข้ามชุด)</p>
              <SimpleTable head={['Cohort', 'Universe', 'Sessions', 'Window', 'Strategy', 'OOS', 'Status']}
                rows={(doc.cohorts ?? []).map((c) => {
                  const excluded = (c.excluded as string[] | undefined) ?? [];
                  const window = (c.evaluation_window ?? {}) as Record<string, string>;
                  return [
                    str(c.cohort_id),
                    `${c.session_count ?? '—'} · excluded ${excluded.length ? excluded.join(', ') : 'none'}`,
                    str(c.session_count),
                    `${window.start ?? '—'} → ${window.end ?? '—'}`,
                    str(c.strategy_id),
                    str(c.out_of_sample_periods),
                    `${str(c.evaluation_status)}${c.comparable_to_established ? '' : ' · not comparable'}`,
                  ];
                })} />
              <p className="text-[11px] text-muted">
                NASA เป็น ETF ที่เริ่มซื้อขาย 2026-03-30 จึงอยู่ในชุด RECENT_INCEPTION เท่านั้น
                และไม่ถูกนำไปเทียบคะแนนกับชุด ESTABLISHED_HISTORY
              </p>
            </div>
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
