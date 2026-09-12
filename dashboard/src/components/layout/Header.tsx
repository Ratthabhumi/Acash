import React from 'react';
import { Search, ShieldAlert, Lock, Activity } from 'lucide-react';
import { CopyablePill } from '../common/CopyablePill';
import { RunMetadata } from '../../types/research';

interface HeaderProps {
  metadata: RunMetadata;
  onOpenCommandPalette: () => void;
}

export const Header: React.FC<HeaderProps> = ({ metadata, onOpenCommandPalette }) => {
  return (
    <header className="sticky top-0 z-30 w-full bg-white/95 backdrop-blur-sm border-b border-enterprise-border px-4 lg:px-6 py-2.5 transition-all">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Left: Branding & Session Info */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center justify-center w-8 h-8 rounded bg-slate-900 text-white font-mono-code font-bold text-xs shadow-xs tracking-wider">
            AC
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-sm font-semibold text-slate-900 tracking-tight">
                ACASH <span className="font-normal text-slate-500">Research & Validation</span>
              </h1>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono-code font-medium bg-slate-100 text-slate-700 border border-slate-200">
                <Activity className="w-3 h-3 text-slate-500" />
                {metadata.strategyId}
              </span>
            </div>
            <div className="flex items-center space-x-2 text-[11px] text-slate-500 font-mono-code mt-0.5">
              <span>Session: {metadata.sessionId}</span>
              <span>·</span>
              <span>Env: {metadata.environment}</span>
            </div>
          </div>
        </div>

        {/* Center/Right: Action Bar & Governance Badges */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Quick Command Trigger */}
          <button
            onClick={onOpenCommandPalette}
            className="flex items-center space-x-2 px-2.5 py-1.5 text-xs text-slate-500 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded transition-colors"
            title="Open Command Palette (Ctrl+K)"
          >
            <Search className="w-3.5 h-3.5 text-slate-400" />
            <span className="hidden sm:inline text-[11px]">Navigate views...</span>
            <kbd className="font-mono-code text-[10px] bg-white border border-slate-300 rounded px-1.5 py-0.5 text-slate-600 shadow-2xs">
              Ctrl+K
            </kbd>
          </button>

          {/* Manifest Hash Pill */}
          <div className="hidden lg:flex items-center">
            <CopyablePill
              label="Manifest"
              value={metadata.manifestHash}
              truncateLength={10}
            />
          </div>

          {/* Research View Only Pill */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono-code font-medium bg-slate-100 text-slate-700 border border-slate-300">
            <Lock className="w-3 h-3 text-slate-500" />
            RESEARCH VIEW ONLY · NO TRADING
          </span>

          {/* Human Authorization Badge */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono-code font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <ShieldAlert className="w-3 h-3 text-rose-600" />
            Human Auth: {metadata.humanAuthorizationStatus.replace('_', ' ')}
          </span>
        </div>
      </div>
    </header>
  );
};
