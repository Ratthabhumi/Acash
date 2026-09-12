import React, { useState, useMemo } from 'react';
import { 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  X, 
  ShieldCheck, 
  Layers, 
  Sparkles, 
  ArrowUpDown 
} from 'lucide-react';
import { TradeRecord, TradeFilterOptions } from '../types/research';
import { StatusBadge } from '../components/common/StatusBadge';


interface TradesPageProps {
  trades: TradeRecord[];
  initialSelectedTradeId?: string | null;
}

export const TradesPage: React.FC<TradesPageProps> = ({
  trades,
  initialSelectedTradeId,
}) => {
  const [filters, setFilters] = useState<TradeFilterOptions>({
    symbol: 'ALL',
    side: 'ALL',
    status: 'ALL',
    searchQuery: '',
  });

  const [sortField, setSortField] = useState<'sequence' | 'pnlBps' | 'durationBars'>('sequence');
  const [sortAsc, setSortAsc] = useState<boolean>(true);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 15;

  const [selectedTrade, setSelectedTrade] = useState<TradeRecord | null>(() => {
    if (initialSelectedTradeId) {
      return trades.find((t) => t.id === initialSelectedTradeId) || null;
    }
    return null;
  });

  // Filter and sort logic
  const filteredTrades = useMemo(() => {
    return trades.filter((t) => {
      if (filters.symbol && filters.symbol !== 'ALL' && t.symbol !== filters.symbol) return false;
      if (filters.side && filters.side !== 'ALL' && t.side !== filters.side) return false;
      if (filters.status && filters.status !== 'ALL') {
        if (filters.status === 'WIN' && t.status !== 'CLOSED_WIN') return false;
        if (filters.status === 'LOSS' && t.status !== 'CLOSED_LOSS') return false;
      }
      if (filters.searchQuery) {
        const q = filters.searchQuery.toLowerCase();
        const matchId = t.id.toLowerCase().includes(q);
        const matchSymbol = t.symbol.toLowerCase().includes(q);
        const matchSig = t.evidenceChain.signalId.toLowerCase().includes(q);
        if (!matchId && !matchSymbol && !matchSig) return false;
      }
      return true;
    }).sort((a, b) => {
      let diff = 0;
      if (sortField === 'sequence') diff = a.sequence - b.sequence;
      if (sortField === 'pnlBps') diff = a.pnlBps - b.pnlBps;
      if (sortField === 'durationBars') diff = a.durationBars - b.durationBars;
      return sortAsc ? diff : -diff;
    });
  }, [trades, filters, sortField, sortAsc]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredTrades.length / pageSize));
  const paginatedTrades = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredTrades.slice(start, start + pageSize);
  }, [filteredTrades, currentPage]);

  // Aggregate stats of current view
  const summaryStats = useMemo(() => {
    const count = filteredTrades.length;
    if (count === 0) return { count: 0, winRate: 0, totalPnlBps: 0, avgR: 0 };
    const wins = filteredTrades.filter((t) => t.status === 'CLOSED_WIN').length;
    const totalPnlBps = filteredTrades.reduce((acc, t) => acc + t.pnlBps, 0);
    const totalR = filteredTrades.reduce((acc, t) => acc + t.rMultiple, 0);
    return {
      count,
      winRate: Math.round((wins / count) * 1000) / 10,
      totalPnlBps: Math.round(totalPnlBps * 10) / 10,
      avgR: Math.round((totalR / count) * 100) / 100,
    };
  }, [filteredTrades]);

  const toggleSort = (field: 'sequence' | 'pnlBps' | 'durationBars') => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Filter and Search Bar */}
      <div className="bg-white rounded-lg border border-enterprise-border p-4 shadow-xs space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Search Box */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Search by Trade ID, Symbol, or Signal ID..."
              value={filters.searchQuery}
              onChange={(e) => {
                setFilters({ ...filters, searchQuery: e.target.value });
                setCurrentPage(1);
              }}
              className="w-full pl-9 pr-3 py-2 rounded border border-slate-200 text-xs font-mono-code placeholder-slate-400 focus:outline-none focus:border-slate-400 bg-slate-50/50"
            />
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono-code">
            {/* Symbol Filter */}
            <select
              value={filters.symbol}
              onChange={(e) => {
                setFilters({ ...filters, symbol: e.target.value });
                setCurrentPage(1);
              }}
              className="px-2.5 py-1.5 rounded border border-slate-200 bg-white text-slate-700 text-xs focus:outline-none"
            >
              <option value="ALL">All Symbols</option>
              <option value="EURUSD">EURUSD</option>
              <option value="GBPUSD">GBPUSD</option>
              <option value="USDJPY">USDJPY</option>
              <option value="AUDUSD">AUDUSD</option>
            </select>

            {/* Side Filter */}
            <select
              value={filters.side}
              onChange={(e) => {
                setFilters({ ...filters, side: e.target.value as 'ALL' | 'LONG' | 'SHORT' });
                setCurrentPage(1);
              }}
              className="px-2.5 py-1.5 rounded border border-slate-200 bg-white text-slate-700 text-xs focus:outline-none"
            >
              <option value="ALL">All Sides</option>
              <option value="LONG">Long</option>
              <option value="SHORT">Short</option>
            </select>

            {/* Status Filter */}
            <select
              value={filters.status}
              onChange={(e) => {
                setFilters({ ...filters, status: e.target.value as 'ALL' | 'WIN' | 'LOSS' });
                setCurrentPage(1);
              }}
              className="px-2.5 py-1.5 rounded border border-slate-200 bg-white text-slate-700 text-xs focus:outline-none"
            >
              <option value="ALL">All Outcomes</option>
              <option value="WIN">Winners</option>
              <option value="LOSS">Losses</option>
            </select>

            {(filters.symbol !== 'ALL' || filters.side !== 'ALL' || filters.status !== 'ALL' || filters.searchQuery) && (
              <button
                onClick={() => {
                  setFilters({ symbol: 'ALL', side: 'ALL', status: 'ALL', searchQuery: '' });
                  setCurrentPage(1);
                }}
                className="px-2 py-1.5 rounded text-[11px] text-slate-500 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                Reset Filters
              </button>
            )}
          </div>
        </div>

        {/* Filter Summary Stats */}
        <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-slate-100 text-xs font-mono-code text-slate-600">
          <div>
            Showing: <span className="font-semibold text-slate-900">{summaryStats.count}</span> of {trades.length} trades
          </div>
          <div>·</div>
          <div>
            Filtered Win Rate: <span className="font-semibold text-slate-900">{summaryStats.winRate}%</span>
          </div>
          <div>·</div>
          <div>
            Cumulative PnL: <span className={`font-semibold ${summaryStats.totalPnlBps >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
              {summaryStats.totalPnlBps >= 0 ? `+${summaryStats.totalPnlBps}` : summaryStats.totalPnlBps} bps
            </span>
          </div>
          <div>·</div>
          <div>
            Avg Expectancy: <span className="font-semibold text-slate-900">{summaryStats.avgR}R</span>
          </div>
        </div>
      </div>

      {/* 2. Trades Table */}
      <div className="bg-white rounded-lg border border-enterprise-border p-4 shadow-xs space-y-3">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono-code">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-[11px]">
                <th className="pb-2 font-medium cursor-pointer hover:text-slate-900" onClick={() => toggleSort('sequence')}>
                  <div className="flex items-center gap-1">
                    <span># / ID</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th className="pb-2 font-medium">Timestamp (UTC)</th>
                <th className="pb-2 font-medium">Symbol</th>
                <th className="pb-2 font-medium">Direction</th>
                <th className="pb-2 font-medium text-right">Entry</th>
                <th className="pb-2 font-medium text-right">Exit</th>
                <th className="pb-2 font-medium text-right cursor-pointer hover:text-slate-900" onClick={() => toggleSort('durationBars')}>
                  <div className="flex items-center justify-end gap-1">
                    <span>Bars</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th className="pb-2 font-medium text-right cursor-pointer hover:text-slate-900" onClick={() => toggleSort('pnlBps')}>
                  <div className="flex items-center justify-end gap-1">
                    <span>PnL (bps)</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th className="pb-2 font-medium text-right">PnL ($)</th>
                <th className="pb-2 font-medium text-right">R-Mult</th>
                <th className="pb-2 font-medium text-center">Status</th>
                <th className="pb-2 font-medium text-right">Audit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedTrades.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => setSelectedTrade(t)}
                  className={`cursor-pointer transition-colors ${
                    selectedTrade?.id === t.id
                      ? 'bg-slate-100/80 font-medium'
                      : 'hover:bg-slate-50/80'
                  }`}
                >
                  <td className="py-2.5 text-slate-900 font-semibold">{t.id}</td>
                  <td className="py-2.5 text-slate-500 text-[11px]">
                    {t.timestamp.slice(0, 16).replace('T', ' ')}
                  </td>
                  <td className="py-2.5 text-slate-700">{t.symbol}</td>
                  <td className="py-2.5">
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
                  <td className="py-2.5 text-right text-slate-600">{t.entryPrice.toFixed(4)}</td>
                  <td className="py-2.5 text-right text-slate-600">{t.exitPrice.toFixed(4)}</td>
                  <td className="py-2.5 text-right text-slate-500">{t.durationBars}</td>
                  <td
                    className={`py-2.5 text-right font-medium ${
                      t.pnlBps >= 0 ? 'text-emerald-700' : 'text-rose-700'
                    }`}
                  >
                    {t.pnlBps >= 0 ? `+${t.pnlBps.toFixed(1)}` : t.pnlBps.toFixed(1)}
                  </td>
                  <td
                    className={`py-2.5 text-right font-medium ${
                      t.pnlUsd >= 0 ? 'text-emerald-700' : 'text-rose-700'
                    }`}
                  >
                    ${t.pnlUsd.toLocaleString()}
                  </td>
                  <td
                    className={`py-2.5 text-right font-medium ${
                      t.rMultiple >= 0 ? 'text-emerald-700' : 'text-rose-700'
                    }`}
                  >
                    {t.rMultiple >= 0 ? `+${t.rMultiple.toFixed(2)}R` : `${t.rMultiple.toFixed(2)}R`}
                  </td>
                  <td className="py-2.5 text-center">
                    <StatusBadge status={t.status === 'CLOSED_WIN' ? 'CLOSED_WIN' : 'CLOSED_LOSS'} />
                  </td>
                  <td className="py-2.5 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedTrade(t);
                      }}
                      className="px-2 py-0.5 rounded text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-colors"
                    >
                      Inspect Chain
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs font-mono-code text-slate-600">
          <div>
            Page <span className="font-semibold text-slate-900">{currentPage}</span> of {totalPages}
          </div>
          <div className="flex items-center space-x-1">
            <button
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="p-1 rounded border border-slate-200 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              className="p-1 rounded border border-slate-200 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 3. Trade Detail & Causal Evidence Chain Modal / Drawer */}
      {selectedTrade && (
        <div className="bg-white rounded-lg border border-slate-300 p-5 shadow-md space-y-4 animate-in fade-in duration-100">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <div className="flex items-center space-x-3">
              <span className="font-mono-code font-bold text-sm text-slate-900">
                Evidence Audit: {selectedTrade.id}
              </span>
              <span className="text-xs font-mono-code px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                {selectedTrade.symbol} · {selectedTrade.side}
              </span>
              <StatusBadge status={selectedTrade.status === 'CLOSED_WIN' ? 'CLOSED_WIN' : 'CLOSED_LOSS'} />
            </div>
            <button
              onClick={() => setSelectedTrade(null)}
              className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* 6-Stage Causal Evidence Flow for this trade */}
          <div>
            <div className="text-xs font-mono-code font-semibold text-slate-700 uppercase tracking-wider mb-3">
              Causal Evidence Chain (Signal → Fill → Portfolio)
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* Stage A: Signal & Feature State */}
              <div className="rounded border border-slate-200 bg-slate-50/70 p-3 space-y-1.5 font-mono-code text-xs">
                <div className="flex items-center justify-between text-slate-500 text-[11px]">
                  <span>1. Signal Generation</span>
                  <Sparkles className="w-3 h-3 text-slate-400" />
                </div>
                <div className="font-semibold text-slate-900">{selectedTrade.evidenceChain.signalId}</div>
                <div className="text-[11px] text-slate-600">
                  Value: <span className="font-semibold">{selectedTrade.evidenceChain.signalValue > 0 ? '+1.0' : '-1.0'}</span>
                </div>
                <div className="text-[11px] text-slate-500 truncate">
                  Feature Hash: {selectedTrade.evidenceChain.featureHash.slice(0, 16)}...
                </div>
              </div>

              {/* Stage B: Risk Gate & Order Intent */}
              <div className="rounded border border-slate-200 bg-slate-50/70 p-3 space-y-1.5 font-mono-code text-xs">
                <div className="flex items-center justify-between text-slate-500 text-[11px]">
                  <span>2. Risk Approval & Intent</span>
                  <ShieldCheck className="w-3 h-3 text-emerald-600" />
                </div>
                <div className="font-semibold text-slate-900">{selectedTrade.evidenceChain.orderIntentId}</div>
                <div className="text-[11px] text-emerald-700 font-medium">
                  Verdict: {selectedTrade.evidenceChain.riskVerdict}
                </div>
                <div className="text-[11px] text-slate-500">
                  Approval ID: {selectedTrade.evidenceChain.riskDecisionId}
                </div>
              </div>

              {/* Stage C: Fill Simulation & Portfolio Impact */}
              <div className="rounded border border-slate-200 bg-slate-50/70 p-3 space-y-1.5 font-mono-code text-xs">
                <div className="flex items-center justify-between text-slate-500 text-[11px]">
                  <span>3. Execution & Impact</span>
                  <Layers className="w-3 h-3 text-slate-400" />
                </div>
                <div className="font-semibold text-slate-900">{selectedTrade.evidenceChain.simulatedFillId}</div>
                <div className="text-[11px] text-slate-600">
                  Slippage: <span className="font-semibold">{selectedTrade.evidenceChain.slippageDeductedBps} bps</span>
                </div>
                <div className="text-[11px] text-slate-700">
                  Portfolio Impact: <span className={selectedTrade.pnlBps >= 0 ? 'text-emerald-700 font-semibold' : 'text-rose-700 font-semibold'}>
                    {selectedTrade.evidenceChain.portfolioImpactBps} bps
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Trade Execution Metrics Summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 font-mono-code text-xs">
            <div className="p-2.5 rounded bg-slate-50 border border-slate-200">
              <div className="text-[11px] text-slate-500">Entry Price</div>
              <div className="font-semibold text-slate-900 text-sm mt-0.5">
                {selectedTrade.entryPrice.toFixed(4)}
              </div>
            </div>
            <div className="p-2.5 rounded bg-slate-50 border border-slate-200">
              <div className="text-[11px] text-slate-500">Exit Price</div>
              <div className="font-semibold text-slate-900 text-sm mt-0.5">
                {selectedTrade.exitPrice.toFixed(4)}
              </div>
            </div>
            <div className="p-2.5 rounded bg-slate-50 border border-slate-200">
              <div className="text-[11px] text-slate-500">Net Realized PnL</div>
              <div className={`font-semibold text-sm mt-0.5 ${selectedTrade.pnlUsd >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                ${selectedTrade.pnlUsd.toLocaleString()} ({selectedTrade.pnlBps.toFixed(1)} bps)
              </div>
            </div>
            <div className="p-2.5 rounded bg-slate-50 border border-slate-200">
              <div className="text-[11px] text-slate-500">Holding Duration</div>
              <div className="font-semibold text-slate-900 text-sm mt-0.5">
                {selectedTrade.durationBars} H4 Bars ({(selectedTrade.durationBars * 4)}h)
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
