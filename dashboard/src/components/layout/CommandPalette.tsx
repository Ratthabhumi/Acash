import React, { useState, useEffect, useRef } from 'react';
import { Search, BarChart3, ArrowLeftRight, GitBranch, ShieldCheck, CornerDownLeft, X } from 'lucide-react';
import { DashboardTab } from './Sidebar';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTab: (tab: DashboardTab) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectTab,
}) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const actions = [
    {
      id: 'overview' as DashboardTab,
      label: 'Navigate to Research Overview',
      subtitle: '90-day simulation metrics, equity curve & timeline',
      icon: BarChart3,
      shortcut: '1',
    },
    {
      id: 'trades' as DashboardTab,
      label: 'Navigate to Simulated Trades',
      subtitle: 'Audit 127 simulated executions & evidence chains',
      icon: ArrowLeftRight,
      shortcut: '2',
    },
    {
      id: 'evidence' as DashboardTab,
      label: 'Navigate to Evidence Lineage',
      subtitle: '11-stage causal DAG & cryptographic artifact verification',
      icon: GitBranch,
      shortcut: '3',
    },
    {
      id: 'validation' as DashboardTab,
      label: 'Navigate to Validation & Gates',
      subtitle: 'Multi-gate statistical evaluation, friction stress & blind OOS',
      icon: ShieldCheck,
      shortcut: '4',
    },
  ];

  const filtered = actions.filter(
    (a) =>
      a.label.toLowerCase().includes(query.toLowerCase()) ||
      a.subtitle.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % (filtered.length || 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + (filtered.length || 1)) % (filtered.length || 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          onSelectTab(filtered[selectedIndex].id);
          onClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filtered, onSelectTab, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-100">
      <div 
        className="w-full max-w-lg bg-surface rounded-lg shadow-xl border border-default overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Header */}
        <div className="flex items-center px-3.5 border-b border-default bg-surface-muted/50">
          <Search className="w-4 h-4 text-muted shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command or jump to view..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            className="w-full px-3 py-3 text-xs text-primary bg-transparent placeholder:text-muted focus:outline-none font-sans"
          />
          <button
            onClick={onClose}
            className="text-muted hover:text-secondary p-1 rounded"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-72 overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-xs text-secondary font-mono-code">
              No matching research navigation commands.
            </div>
          ) : (
            filtered.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    onSelectTab(item.id);
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2.5 rounded cursor-pointer transition-colors text-xs ${
                    isSelected
                      ? 'bg-surface-muted text-primary'
                      : 'text-secondary hover:bg-surface-muted'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div
                      className={`p-1.5 rounded ${
                        isSelected
                          ? 'bg-accent text-white'
                          : 'bg-surface-muted text-muted'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="font-medium text-primary">{item.label}</div>
                      <div className="text-[11px] text-secondary">{item.subtitle}</div>
                    </div>
                  </div>
                  {isSelected && (
                    <div className="flex items-center space-x-1 text-[11px] text-muted font-mono-code">
                      <span>Select</span>
                      <CornerDownLeft className="w-3 h-3" />
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-3.5 py-2 bg-surface-muted/60 border-t border-default flex items-center justify-between text-[11px] text-secondary font-mono-code">
          <span>Lightweight Navigation Shell · Zero execution authority</span>
          <div className="flex items-center space-x-2">
            <span>Use ↑↓ to navigate</span>
            <span>·</span>
            <span>ESC to close</span>
          </div>
        </div>
      </div>
    </div>
  );
};
