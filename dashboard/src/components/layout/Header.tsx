import React from 'react';
import { Search, ShieldAlert, Lock, Activity, Menu, X, Sun, Moon } from 'lucide-react';
import { CopyablePill } from '../common/CopyablePill';
import { RunMetadata } from '../../types/research';
import { useTheme } from '../../context/ThemeContext';

interface HeaderProps {
  metadata: RunMetadata;
  onOpenCommandPalette: () => void;
  isMobileMenuOpen?: boolean;
  onToggleMobileMenu?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  metadata,
  onOpenCommandPalette,
  isMobileMenuOpen,
  onToggleMobileMenu,
}) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-30 w-full bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-b border-enterprise-border dark:border-slate-800 px-4 lg:px-6 py-2.5 lg:py-0 lg:h-14 flex items-center transition-all">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2.5 lg:gap-3 w-full">
        {/* Left: Branding & Session Info */}
        <div className="flex items-center space-x-3">
          {/* Mobile Menu Toggle Button */}
          {onToggleMobileMenu && (
            <button
              onClick={onToggleMobileMenu}
              className="lg:hidden p-1.5 rounded text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white border border-slate-200 dark:border-slate-700 shrink-0"
              aria-label="Toggle navigation menu"
            >
              {isMobileMenuOpen ? (
                <X className="w-4 h-4 text-slate-700 dark:text-slate-300" />
              ) : (
                <Menu className="w-4 h-4 text-slate-700 dark:text-slate-300" />
              )}
            </button>
          )}

          <div className="flex items-center justify-center w-8 h-8 rounded bg-slate-900 dark:bg-slate-800 border border-transparent dark:border-slate-700 text-white font-mono-code font-bold text-xs shadow-xs tracking-wider shrink-0">
            AC
          </div>
          <div className="min-w-0">
            <div className="flex items-center space-x-2 flex-wrap">
              <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100 tracking-tight whitespace-nowrap">
                ACASH <span className="font-normal text-slate-500 dark:text-slate-400">Research & Validation</span>
              </h1>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono-code font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 shrink-0">
                <Activity className="w-3 h-3 text-slate-500 dark:text-slate-400" />
                {metadata.strategyId}
              </span>
            </div>
            <div className="flex items-center space-x-2 text-[11px] text-slate-500 dark:text-slate-400 font-mono-code mt-0.5 truncate">
              <span>Session: {metadata.sessionId}</span>
              <span>·</span>
              <span>Env: {metadata.environment}</span>
            </div>
          </div>
        </div>

        {/* Center/Right: Action Bar & Governance Badges */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Quick Command Trigger */}
          <button
            onClick={onOpenCommandPalette}
            className="flex items-center space-x-1.5 px-2.5 py-1 text-xs text-slate-500 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/90 hover:bg-slate-100 dark:hover:bg-slate-750 border border-slate-200 dark:border-slate-700 rounded transition-colors"
            title="Open Command Palette (Ctrl+K)"
          >
            <Search className="w-3.5 h-3.5 text-slate-400 dark:text-slate-400" />
            <span className="hidden sm:inline text-[11px]">Navigate views...</span>
            <kbd className="font-mono-code text-[10px] bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded px-1.5 py-0.5 text-slate-600 dark:text-slate-400 shadow-2xs">
              Ctrl+K
            </kbd>
          </button>

          {/* Theme Toggle (Light / Dark) */}
          <button
            onClick={toggleTheme}
            className="flex items-center justify-center p-1.5 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white transition-colors shrink-0"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? (
              <Sun className="w-3.5 h-3.5 text-amber-400" />
            ) : (
              <Moon className="w-3.5 h-3.5 text-slate-600" />
            )}
          </button>

          {/* Manifest Hash Pill */}
          <div className="hidden xl:flex items-center">
            <CopyablePill
              label="Manifest"
              value={metadata.manifestHash}
              truncateLength={10}
            />
          </div>

          {/* Research View Only Pill */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono-code font-medium bg-slate-100 dark:bg-slate-800/90 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 shrink-0 whitespace-nowrap">
            <Lock className="w-3 h-3 text-slate-500 dark:text-slate-400 shrink-0" />
            RESEARCH VIEW ONLY · NO TRADING
          </span>

          {/* Human Authorization Badge */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono-code font-semibold bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800/60 shrink-0 whitespace-nowrap">
            <ShieldAlert className="w-3 h-3 text-rose-600 dark:text-rose-400 shrink-0" />
            Human Auth: {metadata.humanAuthorizationStatus.replace('_', ' ')}
          </span>
        </div>
      </div>
    </header>
  );
};
