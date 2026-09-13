/**
 * ACASH Shadow Alpha Tournament — Dashboard Page
 *
 * PRIMARY OPERATOR INTERFACE for the Shadow Tournament.
 * READ-ONLY: zero mutation controls. No start/stop/deploy buttons.
 *
 * Governance badges are always visible and cannot be dismissed.
 *
 * SHADOW / SIMULATED ONLY — NOT Paper — NOT Live — NOT HYP_003
 * CANONICAL CAPITAL = $0.00 | REAL ORDERS = 0
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  ShieldAlert,
  Lock,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Wifi,
  WifiOff,
  Trophy,
  Clock,
  RefreshCw,
  Info,
} from 'lucide-react';
import {
  TournamentState,
  ShadowApiResponse,
  SlotId,
  StrategySlot,
  FeedHealth,
  SlotStatus,
  SHADOW_GOVERNANCE,
} from '../types/shadow';
import { shadowRepository } from '../services/shadowRepository';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDuration(seconds: number): string {
  if (seconds <= 0) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatPct(val: number, decimals = 2): string {
  const sign = val >= 0 ? '+' : '';
  return `${sign}${val.toFixed(decimals)}%`;
}

function formatUsd(val: number): string {
  return `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function timeSince(isoUtc: string | null): string {
  if (!isoUtc) return '—';
  const ms = Date.now() - new Date(isoUtc).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m ago`;
}

// ---------------------------------------------------------------------------
// Small shared components
// ---------------------------------------------------------------------------

const GovernanceBanner: React.FC = () => (
  <div
    className="flex flex-wrap items-center gap-2 p-3 rounded-lg border border-rose-200 dark:border-rose-800/60
      bg-rose-50 dark:bg-rose-950/30 text-xs font-mono"
    role="alert"
    aria-label="Governance boundary notice"
  >
    <ShieldAlert className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
    <span className="text-rose-700 dark:text-rose-300 font-semibold tracking-wide">
      SHADOW / SIMULATED ONLY
    </span>
    <span className="text-rose-500 dark:text-rose-400">·</span>
    <span className="text-rose-600 dark:text-rose-400">REAL CAPITAL = $0.00</span>
    <span className="text-rose-500 dark:text-rose-400">·</span>
    <span className="text-rose-600 dark:text-rose-400">REAL ORDERS = {SHADOW_GOVERNANCE.REAL_ORDERS}</span>
    <span className="text-rose-500 dark:text-rose-400">·</span>
    <span className="text-rose-600 dark:text-rose-400">NO_REAL_ORDERS = true</span>
    <span className="text-rose-500 dark:text-rose-400">·</span>
    <span className="text-rose-600 dark:text-rose-400">NOT Paper · NOT Live · NOT HYP_003</span>
    <Lock className="w-3.5 h-3.5 text-rose-500 dark:text-rose-400 shrink-0 ml-auto" />
  </div>
);

interface FeedHealthBadgeProps { health: FeedHealth }
const FeedHealthBadge: React.FC<FeedHealthBadgeProps> = ({ health }) => {
  const cfg: Record<FeedHealth, { label: string; cls: string; Icon: React.FC<{ className?: string }> }> = {
    HEALTHY:      { label: 'Feed HEALTHY',      cls: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800/60', Icon: Wifi },
    STALE:        { label: 'Feed STALE',        cls: 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800/60', Icon: AlertTriangle },
    HALTED:       { label: 'Feed HALTED',       cls: 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-800/60', Icon: WifiOff },
    DISCONNECTED: { label: 'Feed DISCONNECTED', cls: 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-800/60', Icon: WifiOff },
    UNKNOWN:      { label: 'Feed UNKNOWN',      cls: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700', Icon: Activity },
  };
  const { label, cls, Icon } = cfg[health] ?? cfg.UNKNOWN;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-[11px] font-mono font-semibold ${cls}`}>
      <Icon className="w-3 h-3 shrink-0" />
      {label}
    </span>
  );
};

interface StatusDotProps { status: SlotStatus }
const StatusDot: React.FC<StatusDotProps> = ({ status }) => {
  const cfg: Record<SlotStatus, string> = {
    RUNNING:      'bg-emerald-500',
    HALTED:       'bg-rose-500',
    UNASSIGNED:   'bg-slate-400',
    ERROR:        'bg-rose-600 animate-pulse',
    INITIALIZING: 'bg-amber-500 animate-pulse',
  };
  return <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${cfg[status] ?? cfg.UNASSIGNED}`} />;
};

// ---------------------------------------------------------------------------
// Strategy Slot Card
// ---------------------------------------------------------------------------

interface SlotCardProps {
  slot: StrategySlot;
  rank: number | null;
}

const SlotCard: React.FC<SlotCardProps> = ({ slot, rank }) => {
  const { slotId, strategyName, strategyVersion, status, metrics, haltReason, acashCommitSha, lastBarUtc } = slot;
  const isUnassigned = status === 'UNASSIGNED';
  const isHalted = status === 'HALTED';

  const pnlPositive = metrics.pnlPct >= 0;

  return (
    <div
      className={`bg-white dark:bg-slate-900 rounded-xl border shadow-sm transition-colors flex flex-col gap-4 p-4
        ${isHalted ? 'border-rose-300 dark:border-rose-800' : 'border-slate-200 dark:border-slate-800'}`}
      aria-label={`Strategy slot ${slotId}: ${strategyName}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-slate-900 dark:bg-slate-800 text-white font-mono font-bold text-sm shrink-0">
            {slotId}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <StatusDot status={status} />
              <span className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
                Slot {slotId}
              </span>
              {rank !== null && (
                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400 text-[10px] font-mono font-bold border border-amber-200 dark:border-amber-800/60 shrink-0">
                  <Trophy className="w-2.5 h-2.5" />
                  #{rank}
                </span>
              )}
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono truncate mt-0.5">
              {isUnassigned ? 'UNASSIGNED — Awaiting Human Strategy Selection' : `${strategyName} v${strategyVersion}`}
            </div>
          </div>
        </div>
        <span className={`shrink-0 px-2 py-0.5 rounded text-[10px] font-mono font-semibold border
          ${isUnassigned ? 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700'
          : isHalted ? 'bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-800'
          : 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'}`}>
          {status}
        </span>
      </div>

      {/* Halt notice */}
      {isHalted && haltReason && (
        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/60 text-xs text-rose-700 dark:text-rose-400">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold mb-0.5">HALTED — OPERATOR RESUME REQUIRED</div>
            <div className="font-mono">{haltReason}</div>
          </div>
        </div>
      )}

      {/* Unassigned notice */}
      {isUnassigned && (
        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-400">
          <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-slate-700 dark:text-slate-300 mb-0.5">Strategy Not Assigned</div>
            <div>Zero alpha candidates currently exist. See H02 in Human Action Queue for strategy selection requirements.</div>
          </div>
        </div>
      )}

      {/* NAV / PnL */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 border border-slate-200 dark:border-slate-700/50">
          <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Virtual NAV</div>
          <div className="text-lg font-bold text-slate-900 dark:text-slate-100 font-mono">
            {formatUsd(metrics.currentNavUsd)}
          </div>
          <div className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">
            Initial: {formatUsd(metrics.initialNavUsd)}
          </div>
        </div>
        <div className={`rounded-lg p-3 border ${pnlPositive
          ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800/50'
          : 'bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800/50'}`}>
          <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Virtual PnL</div>
          <div className={`text-lg font-bold font-mono flex items-center gap-1 ${pnlPositive ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-400'}`}>
            {pnlPositive ? <TrendingUp className="w-4 h-4 shrink-0" /> : <TrendingDown className="w-4 h-4 shrink-0" />}
            {formatPct(metrics.pnlPct)}
          </div>
          <div className={`text-[10px] font-mono ${pnlPositive ? 'text-emerald-600 dark:text-emerald-500' : 'text-rose-600 dark:text-rose-500'}`}>
            {formatUsd(metrics.pnlUsd)}
          </div>
        </div>
      </div>

      {/* Key metrics grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-[11px] font-mono">
        {[
          { label: 'Realized PnL', value: formatUsd(metrics.realizedPnlUsd) },
          { label: 'Unrealized PnL', value: formatUsd(metrics.unrealizedPnlUsd) },
          { label: 'Max Drawdown', value: metrics.maxDrawdownPct === 0 ? '—' : `-${metrics.maxDrawdownPct.toFixed(2)}%` },
          { label: 'Curr. Drawdown', value: metrics.currentDrawdownPct === 0 ? '—' : `-${metrics.currentDrawdownPct.toFixed(2)}%` },
          { label: 'Risk Util.', value: `${metrics.riskUtilizationPct.toFixed(1)}%` },
          { label: 'Exposure', value: `${metrics.exposurePct.toFixed(1)}%` },
          { label: 'Open Positions', value: String(metrics.openPositionCount) },
          { label: 'Sim. Fills', value: String(metrics.simulatedFillCount) },
          { label: 'Win Rate', value: metrics.winRatePct !== null ? `${metrics.winRatePct.toFixed(1)}%` : '— (n<2)' },
          { label: 'Signals', value: String(metrics.signalCount) },
          { label: 'Last Signal', value: timeSince(metrics.lastSignalUtc) },
          { label: 'Runtime', value: formatDuration(metrics.durationSeconds) },
        ].map(({ label, value }) => (
          <div key={label} className="flex justify-between items-center py-0.5 border-b border-slate-100 dark:border-slate-800">
            <span className="text-slate-500 dark:text-slate-400">{label}</span>
            <span className="text-slate-800 dark:text-slate-200 font-medium">{value}</span>
          </div>
        ))}
      </div>

      {/* Commit SHA */}
      <div className="text-[10px] font-mono text-slate-400 dark:text-slate-600 truncate">
        ACASH: {acashCommitSha.slice(0, 12)}…
        {lastBarUtc && <span className="ml-2">· Last bar: {timeSince(lastBarUtc)}</span>}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Global Status Bar (mobile-optimized)
// ---------------------------------------------------------------------------

interface GlobalStatusBarProps {
  global: TournamentState['global'];
  fetchedAt: string;
  isMock: boolean;
}

const GlobalStatusBar: React.FC<GlobalStatusBarProps> = ({ global, fetchedAt, isMock }) => (
  <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-4 space-y-3">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex items-center gap-2">
        <Activity className="w-4 h-4 text-slate-500 dark:text-slate-400" />
        <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">{global.label}</span>
        {isMock && (
          <span className="px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400 text-[10px] font-mono font-bold border border-amber-200 dark:border-amber-800/60">
            MOCK DATA
          </span>
        )}
      </div>
      <FeedHealthBadge health={global.feedHealth} />
    </div>

    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 text-[11px] font-mono">
      {[
        { label: 'Real Capital', value: formatUsd(global.canonicalCapitalUsd), warn: false },
        { label: 'Real Orders', value: String(global.realOrderCount), warn: global.realOrderCount > 0 },
        { label: 'NO_REAL_ORDERS', value: String(global.noRealOrders), warn: !global.noRealOrders },
        { label: 'Overall Status', value: global.overallStatus, warn: global.overallStatus === 'HALTED' },
        { label: 'Runtime', value: formatDuration(global.runtimeUptimeSeconds), warn: false },
        { label: 'Last Data', value: timeSince(global.lastDataTimestampUtc), warn: false },
        { label: 'Updated', value: timeSince(global.lastSuccessfulUpdateUtc), warn: false },
        { label: 'ACASH SHA', value: global.acashCommitSha.slice(0, 8) + '…', warn: false },
      ].map(({ label, value, warn }) => (
        <div key={label} className="flex flex-col gap-0.5">
          <span className="text-slate-400 dark:text-slate-500 uppercase tracking-wider text-[9px]">{label}</span>
          <span className={`font-medium ${warn ? 'text-rose-600 dark:text-rose-400' : 'text-slate-800 dark:text-slate-200'}`}>
            {value}
          </span>
        </div>
      ))}
    </div>

    {global.haltReason && (
      <div className="flex items-start gap-2 p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/60 text-xs">
        <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-rose-600 dark:text-rose-400" />
        <div className="text-rose-700 dark:text-rose-400 font-mono">{global.haltReason}</div>
      </div>
    )}

    <div className="flex items-center gap-1.5 text-[10px] text-slate-400 dark:text-slate-500 font-mono">
      <Clock className="w-3 h-3" />
      <span>Fetched: {new Date(fetchedAt).toLocaleTimeString()}</span>
      <span>·</span>
      <span>Image: {global.deploymentImageId}</span>
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Leaderboard
// ---------------------------------------------------------------------------

interface LeaderboardProps {
  tournament: TournamentState;
}

const Leaderboard: React.FC<LeaderboardProps> = ({ tournament }) => {
  const { leaderboard, slots } = tournament;

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-4">
      <div className="flex items-center gap-2 mb-3">
        <Trophy className="w-4 h-4 text-amber-500" />
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Leaderboard</h3>
        <span className={`ml-auto px-2 py-0.5 rounded text-[10px] font-mono font-medium border
          ${leaderboard.comparisonAvailability === 'INSUFFICIENT_SAMPLE'
            ? 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700'
            : 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800/60'}`}>
          {leaderboard.comparisonAvailability.replace(/_/g, ' ')}
        </span>
      </div>

      <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono mb-3 p-2 bg-slate-50 dark:bg-slate-800/50 rounded border border-slate-100 dark:border-slate-700">
        <Info className="w-3 h-3 inline mr-1" />
        {leaderboard.comparisonNote}
      </div>

      {leaderboard.rankedSlots.length === 0 ? (
        <div className="text-center text-xs text-slate-400 dark:text-slate-500 font-mono py-6">
          No runtime data available yet.
          <br />
          Tournament must be started and strategies assigned.
        </div>
      ) : (
        <div className="space-y-2">
          {leaderboard.rankedSlots.map(({ rank, slotId, strategyName, pnlPct, maxDrawdownPct, navUsd }) => {
            const slot = slots[slotId];
            const positive = pnlPct >= 0;
            return (
              <div
                key={slotId}
                className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700/50"
              >
                <div className="w-7 h-7 flex items-center justify-center rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-bold text-sm">
                  {rank}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <StatusDot status={slot?.status ?? 'UNASSIGNED'} />
                    <span className="text-xs font-semibold text-slate-800 dark:text-slate-100">Slot {slotId}</span>
                    <span className="text-[10px] text-slate-400 dark:text-slate-500 truncate font-mono">{strategyName}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                    Max DD: {maxDrawdownPct === 0 ? '—' : `-${maxDrawdownPct.toFixed(2)}%`}
                    &nbsp;·&nbsp;NAV: {formatUsd(navUsd)}
                  </div>
                </div>
                <div className={`text-sm font-bold font-mono flex items-center gap-1 ${positive ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                  {positive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                  {formatPct(pnlPct)}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export const ShadowTournamentPage: React.FC = () => {
  const [response, setResponse] = useState<ShadowApiResponse<TournamentState> | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleUpdate = useCallback((resp: ShadowApiResponse<TournamentState>) => {
    setResponse(resp);
  }, []);

  useEffect(() => {
    const unsubscribe = shadowRepository.subscribe(handleUpdate);
    return unsubscribe;
  }, [handleUpdate]);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    try {
      const result = await shadowRepository.getState();
      setResponse(result);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Loading state
  if (response === null) {
    return (
      <div className="space-y-4">
        <GovernanceBanner />
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-slate-200 dark:bg-slate-800 rounded-xl" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="h-64 bg-slate-200 dark:bg-slate-800 rounded-xl" />
            <div className="h-64 bg-slate-200 dark:bg-slate-800 rounded-xl" />
            <div className="h-64 bg-slate-200 dark:bg-slate-800 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  // API error state — show visibly, never fabricate
  if (!response.ok || !response.data) {
    return (
      <div className="space-y-4">
        <GovernanceBanner />
        <div className="bg-rose-50 dark:bg-rose-950/30 rounded-xl border border-rose-200 dark:border-rose-800/60 p-6">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400" />
            <h3 className="text-sm font-semibold text-rose-700 dark:text-rose-300">Shadow API Unavailable</h3>
          </div>
          <p className="text-xs text-rose-600 dark:text-rose-400 font-mono mb-3">
            {response.error ?? 'Unknown error fetching tournament state.'}
          </p>
          <p className="text-[11px] text-rose-500 dark:text-rose-500 font-mono">
            Dashboard refuses to fabricate state. Waiting for backend.
          </p>
          <button
            onClick={() => void handleManualRefresh()}
            className="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded border border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-400 text-xs font-mono hover:bg-rose-100 dark:hover:bg-rose-900/30 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            Retry
          </button>
        </div>
      </div>
    );
  }

  const { data: tournament } = response;
  const slots: SlotId[] = ['A', 'B', 'C'];
  const isMock = tournament._meta.isMockData;

  // Build rank map from leaderboard
  const rankMap = new Map<SlotId, number>();
  tournament.leaderboard.rankedSlots.forEach(({ rank, slotId }) => rankMap.set(slotId, rank));

  return (
    <div className="space-y-4">
      {/* 1. Permanent governance banner */}
      <GovernanceBanner />

      {/* Mock data notice */}
      {isMock && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 text-xs">
          <Info className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
          <div className="text-amber-700 dark:text-amber-400 font-mono">
            <span className="font-semibold">MOCK DEMO DATA</span>
            {' '}· No live runtime connected. Connect a backend at{' '}
            <code className="bg-amber-100 dark:bg-amber-900/40 px-1 rounded">VITE_SHADOW_API_URL</code>
            {' '}to see live tournament data.
          </div>
          <button
            onClick={() => void handleManualRefresh()}
            className="ml-auto shrink-0 p-1 rounded text-amber-600 dark:text-amber-400 hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      )}

      {/* 2. Global status bar */}
      <GlobalStatusBar
        global={tournament.global}
        fetchedAt={tournament._meta.fetchedAtUtc}
        isMock={isMock}
      />

      {/* 3. Strategy slots — mobile: stack; tablet+: 3 columns */}
      <div>
        <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
          Strategy Slots — Virtual $1,000 NAV each
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {slots.map((id) => (
            <SlotCard
              key={id}
              slot={tournament.slots[id]}
              rank={rankMap.get(id) ?? null}
            />
          ))}
        </div>
      </div>

      {/* 4. Leaderboard */}
      <Leaderboard tournament={tournament} />

      {/* 5. Architecture invariants footer */}
      <div className="bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center gap-2 mb-2">
          <Lock className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
          <span className="text-[11px] font-mono font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
            Architecture Invariants
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-[10px] font-mono text-slate-500 dark:text-slate-500">
          {[
            ['Dashboard', 'READ ONLY — zero mutation controls'],
            ['Broker Dispatch', 'STRUCTURALLY DISABLED'],
            ['Real Credentials', 'NOT PRESENT in tournament runtime'],
            ['Auto Code Sync', 'DISABLED — builds are pinned'],
            ['Auto Feed Reconnect', 'DISABLED — operator resume required'],
            ['Public Internet', 'DISABLED — Tailscale private tailnet only'],
            ['Watchtower', 'DISABLED for ACASH containers'],
            ['G7 / S11', 'CLOSED / PASS — unchanged'],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <span className="text-slate-400 dark:text-slate-600">{k}:</span>
              <span className="text-slate-600 dark:text-slate-400">{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
