import React, { useState } from 'react';
import { ChevronRight, Info } from 'lucide-react';
import { ResearchRun, TimelineEvent } from '../types/research';
import { MetricCard } from '../components/common/MetricCard';
import { CopyablePill } from '../components/common/CopyablePill';
import { StatusBadge } from '../components/common/StatusBadge';
import { EquityDrawdownChart } from '../components/charts/EquityDrawdownChart';
import { DashboardTab } from '../components/layout/Sidebar';

interface OverviewPageProps {
  researchRun: ResearchRun;
  onNavigateTab: (tab: DashboardTab) => void;
  onSelectTradeId?: (tradeId: string) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  researchRun,
  onNavigateTab,
  onSelectTradeId,
}) => {
  const { metadata, dataset, config, metrics, equityCurve, timelineEvents, validationCriteria, trades } = researchRun;
  const [selectedEvent, setSelectedEvent] = useState<TimelineEvent | null>(null);

  const recentTrades = trades.slice(Math.max(0, trades.length - 6)).reverse();

  return (
    <div className="space-y-6">
      {/* 1. Top Metadata Information Bar */}
      <div className="bg-white rounded-lg border border-enterprise-border p-4 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold text-slate-900 tracking-tight">
                {metadata.strategyId}
              </h2>
              <span className="text-xs font-mono-code px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                v{metadata.strategyVersion}
              </span>
              <span className="text-[11px] font-mono-code px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 font-medium">
                SIMULATED RUN
              </span>
            </div>
            <p className="text-xs text-slate-500 font-mono-code">
              {metadata.dataSource} · Timeframe: {dataset.timeframe} · Bars: {dataset.barCount.toLocaleString()}
            </p>
          </div>

          {/* Cryptographic Lineage Pills */}
          <div className="flex flex-wrap items-center gap-2">
            <CopyablePill label="Commit" value={metadata.gitCommit} truncateLength={7} />
            <CopyablePill label="Config" value={config.configHash} truncateLength={8} />
            <CopyablePill label="Batch" value={dataset.canonicalBatchSha256} truncateLength={8} />
          </div>
        </div>
      </div>

      {/* 2. Key 8 Metric Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Net Cumulative Return"
          value={`+${metrics.netReturnPct.toFixed(2)}%`}
          subValue="After 1.2 bps total friction"
          trend="up"
        />
        <MetricCard
          label="Observed Sharpe (Ann.)"
          value={metrics.sharpeRatio.toFixed(2)}
          subValue="H4 bar sample (Unverified)"
          trend="neutral"
        />
        <MetricCard
          label="Maximum Drawdown"
          value={`-${metrics.maxDrawdownPct.toFixed(2)}%`}
          subValue="Peak-to-trough observed"
          trend="down"
        />
        <MetricCard
          label="Simulated Trades"
          value={metrics.totalTrades}
          subValue={`Win rate: ${metrics.winRatePct.toFixed(1)}%`}
          trend="neutral"
        />
        <MetricCard
          label="Profit Factor"
          value={metrics.profitFactor.toFixed(2)}
          subValue={`Expectancy: +${metrics.expectancyR.toFixed(2)}R`}
          trend="up"
        />
        <MetricCard
          label="Gross Return (Pre-Friction)"
          value={`+${metrics.grossReturnPct.toFixed(2)}%`}
          subValue="Theoretical zero-drag"
          trend="neutral"
        />
        <MetricCard
          label="Cumulative Friction Drag"
          value={`-${metrics.totalFrictionCostPct.toFixed(2)}%`}
          subValue="Spread + Fee + Slippage"
          trend="down"
        />
        <MetricCard
          label="Capital Authority"
          value="$0.00"
          subValue="Trading Engine: DISABLED"
          trend="neutral"
        />
      </div>

      {/* 3. Primary Chart: Equity Curve & Drawdown */}
      <EquityDrawdownChart data={equityCurve} />

      {/* 4. Split Grid: Friction Waterfall & Validation Quick Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gross-to-Net Friction Breakdown */}
        <div className="bg-white rounded-lg border border-enterprise-border p-4 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div>
              <h3 className="text-xs font-semibold text-slate-900 tracking-tight">
                Gross-to-Net Friction Attribution
              </h3>
              <p className="text-[11px] text-slate-500 font-mono-code mt-0.5">
                Stress decay across 127 executed fills
              </p>
            </div>
            <button
              onClick={() => onNavigateTab('validation')}
              className="text-xs font-mono-code text-slate-600 hover:text-slate-900 flex items-center gap-1 transition-colors"
            >
              <span>View Gates</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3 font-mono-code text-xs">
            <div className="flex justify-between items-center py-1.5 border-b border-slate-50">
              <span className="text-slate-600">Gross Simulated Potential</span>
              <span className="font-semibold text-slate-900">+{metrics.grossReturnPct.toFixed(2)}%</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-slate-50 text-rose-700">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                Quoted Bid/Ask Spread (0.4 bps/trade)
              </span>
              <span>-{(metrics.totalFrictionCostPct * 0.33).toFixed(2)}%</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-slate-50 text-rose-700">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                Execution Fees (0.5 bps/trade)
              </span>
              <span>-{metrics.feesPaidPct.toFixed(2)}%</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-slate-50 text-rose-700">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                Conservative Slippage Model (0.3 bps/trade)
              </span>
              <span>-{metrics.slippageIncurredPct.toFixed(2)}%</span>
            </div>
            <div className="flex justify-between items-center pt-2 font-semibold text-slate-900 bg-slate-50/80 p-2 rounded">
              <span>Net Empirical Performance</span>
              <span className="text-emerald-700">+{metrics.netReturnPct.toFixed(2)}%</span>
            </div>
          </div>
        </div>

        {/* Validation Checklist Snapshot */}
        <div className="bg-white rounded-lg border border-enterprise-border p-4 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div>
              <h3 className="text-xs font-semibold text-slate-900 tracking-tight">
                Statistical Gate Status Snapshot
              </h3>
              <p className="text-[11px] text-slate-500 font-mono-code mt-0.5">
                Canonical Research Standards · Zero Fake Pass
              </p>
            </div>
            <button
              onClick={() => onNavigateTab('validation')}
              className="text-xs font-mono-code text-slate-600 hover:text-slate-900 flex items-center gap-1 transition-colors"
            >
              <span>Audit Details</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2">
            {validationCriteria.slice(0, 4).map((crit) => (
              <div
                key={crit.id}
                className="flex items-center justify-between p-2 rounded bg-slate-50/60 border border-slate-100 text-xs"
              >
                <div className="truncate pr-2">
                  <div className="font-medium text-slate-900 truncate">{crit.name}</div>
                  <div className="text-[11px] text-slate-500 font-mono-code truncate">
                    {crit.ruleSpecification}
                  </div>
                </div>
                <StatusBadge status={crit.status} />
              </div>
            ))}
          </div>

          <div className="pt-1 text-[11px] text-slate-500 font-mono-code flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span>Out-of-sample partitions remain strictly unexposed.</span>
          </div>
        </div>
      </div>

      {/* 5. 90-Day Simulation Timeline & Events */}
      <div className="bg-white rounded-lg border border-enterprise-border p-4 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
          <div>
            <h3 className="text-xs font-semibold text-slate-900 tracking-tight">
              Simulation Milestone Timeline (90-Day Chronology)
            </h3>
            <p className="text-[11px] text-slate-500 font-mono-code mt-0.5">
              Click any milestone to inspect structured telemetry payload
            </p>
          </div>
          <span className="text-[11px] font-mono-code px-2 py-0.5 rounded bg-slate-100 text-slate-600">
            {timelineEvents.length} Recorded Milestones
          </span>
        </div>

        <div className="relative pl-6 space-y-4 border-l border-slate-200 ml-2">
          {timelineEvents.map((evt) => (
            <div
              key={evt.id}
              onClick={() => setSelectedEvent(evt)}
              className={`group cursor-pointer p-3 rounded-md border transition-all text-xs ${
                selectedEvent?.id === evt.id
                  ? 'border-slate-900 bg-slate-50 shadow-xs'
                  : 'border-slate-100 bg-white hover:border-slate-300 hover:bg-slate-50/50'
              }`}
            >
              {/* Timeline Marker Bullet */}
              <div className="absolute -left-[7px] mt-1.5 w-3 h-3 rounded-full border-2 border-white bg-slate-600 group-hover:bg-slate-900 transition-colors" />

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
                <div className="flex items-center space-x-2">
                  <span className="font-mono-code font-semibold text-slate-900">
                    {evt.title}
                  </span>
                  <span className="text-[10px] font-mono-code px-1.5 py-0.2 rounded bg-slate-100 text-slate-600">
                    {evt.category}
                  </span>
                </div>
                <span className="text-[11px] font-mono-code text-slate-400">
                  {new Date(evt.timestamp).toUTCString().slice(5, 22)}
                </span>
              </div>
              <p className="text-slate-600 text-[11px] leading-relaxed">
                {evt.summary}
              </p>
            </div>
          ))}
        </div>

        {/* Selected Event Payload Detail Modal / Drawer */}
        {selectedEvent && (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs space-y-2 font-mono-code animate-in fade-in duration-100">
            <div className="flex items-center justify-between border-b border-slate-200 pb-1.5">
              <span className="font-semibold text-slate-800">
                Payload Telemetry: {selectedEvent.id} ({selectedEvent.title})
              </span>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-slate-400 hover:text-slate-600 text-[11px]"
              >
                Close Drawer
              </button>
            </div>
            <pre className="text-[11px] text-slate-700 overflow-x-auto p-2 rounded bg-white border border-slate-200">
              {JSON.stringify(selectedEvent.payload, null, 2)}
            </pre>
            {selectedEvent.relatedTradeId && (
              <div className="flex items-center gap-2 pt-1 text-[11px]">
                <span className="text-slate-500">Related Trade:</span>
                <button
                  onClick={() => {
                    onNavigateTab('trades');
                    if (onSelectTradeId) onSelectTradeId(selectedEvent.relatedTradeId!);
                  }}
                  className="text-slate-900 underline font-medium hover:text-blue-600"
                >
                  {selectedEvent.relatedTradeId}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 6. Recent Simulated Executions Preview */}
      <div className="bg-white rounded-lg border border-enterprise-border p-4 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
          <div>
            <h3 className="text-xs font-semibold text-slate-900 tracking-tight">
              Recent Simulated Executions (Sample 6 of {trades.length})
            </h3>
            <p className="text-[11px] text-slate-500 font-mono-code mt-0.5">
              Strict next-bar open fill simulation with 1.2 bps friction deduction
            </p>
          </div>
          <button
            onClick={() => onNavigateTab('trades')}
            className="text-xs font-mono-code text-slate-600 hover:text-slate-900 flex items-center gap-1 transition-colors"
          >
            <span>Open All 127 Trades</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono-code">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-[11px]">
                <th className="pb-2 font-medium">Trade ID</th>
                <th className="pb-2 font-medium">Date (UTC)</th>
                <th className="pb-2 font-medium">Symbol</th>
                <th className="pb-2 font-medium">Side</th>
                <th className="pb-2 font-medium text-right">Entry</th>
                <th className="pb-2 font-medium text-right">Exit</th>
                <th className="pb-2 font-medium text-right">PnL (bps)</th>
                <th className="pb-2 font-medium text-right">PnL ($)</th>
                <th className="pb-2 font-medium text-right">R-Mult</th>
                <th className="pb-2 font-medium text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {recentTrades.map((t) => (
                <tr key={t.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-2 text-slate-900 font-semibold">{t.id}</td>
                  <td className="py-2 text-slate-500 text-[11px]">{t.timestamp.slice(0, 16).replace('T', ' ')}</td>
                  <td className="py-2 text-slate-700">{t.symbol}</td>
                  <td className="py-2">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        t.side === 'LONG'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}
                    >
                      {t.side}
                    </span>
                  </td>
                  <td className="py-2 text-right text-slate-600">{t.entryPrice.toFixed(4)}</td>
                  <td className="py-2 text-right text-slate-600">{t.exitPrice.toFixed(4)}</td>
                  <td
                    className={`py-2 text-right font-medium ${
                      t.pnlBps >= 0 ? 'text-emerald-700' : 'text-rose-700'
                    }`}
                  >
                    {t.pnlBps >= 0 ? `+${t.pnlBps}` : t.pnlBps}
                  </td>
                  <td
                    className={`py-2 text-right font-medium ${
                      t.pnlUsd >= 0 ? 'text-emerald-700' : 'text-rose-700'
                    }`}
                  >
                    ${t.pnlUsd.toLocaleString()}
                  </td>
                  <td
                    className={`py-2 text-right font-medium ${
                      t.rMultiple >= 0 ? 'text-emerald-700' : 'text-rose-700'
                    }`}
                  >
                    {t.rMultiple >= 0 ? `+${t.rMultiple}R` : `${t.rMultiple}R`}
                  </td>
                  <td className="py-2 text-center">
                    <StatusBadge status={t.status === 'CLOSED_WIN' ? 'CLOSED_WIN' : 'CLOSED_LOSS'} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
