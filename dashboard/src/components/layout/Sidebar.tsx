import React from 'react';
import { 
  BarChart3, 
  ArrowLeftRight, 
  GitBranch, 
  ShieldCheck, 
  Database, 
  Lock, 
  Layers,
  X,
  Swords
} from 'lucide-react';

export type DashboardTab = 'overview' | 'trades' | 'evidence' | 'validation' | 'shadow';

interface SidebarProps {
  currentTab: DashboardTab;
  onSelectTab: (tab: DashboardTab) => void;
  tradeCount: number;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  tradeCount,
  isMobileOpen,
  onCloseMobile,
}) => {
  const navItems = [
    {
      id: 'overview' as DashboardTab,
      label: 'Research Overview',
      icon: BarChart3,
      badge: '90D',
      description: 'Metrics, equity curve & timeline',
    },
    {
      id: 'trades' as DashboardTab,
      label: 'Simulated Trades',
      icon: ArrowLeftRight,
      badge: String(tradeCount),
      description: 'Causal trade audit & evidence',
    },
    {
      id: 'evidence' as DashboardTab,
      label: 'Evidence Lineage',
      icon: GitBranch,
      badge: '11 Stages',
      description: 'Causal DAG & cryptographic artifacts',
    },
    {
      id: 'validation' as DashboardTab,
      label: 'Validation & Gates',
      icon: ShieldCheck,
      badge: 'Gated',
      description: 'Statistical criteria & blind OOS',
    },
    {
      id: 'shadow' as DashboardTab,
      label: 'Shadow Tournament',
      icon: Swords,
      badge: 'SIMULATED',
      description: 'Shadow alpha tournament — read-only',
    },
  ];

  const handleNavClick = (tabId: DashboardTab) => {
    onSelectTab(tabId);
    if (onCloseMobile) {
      onCloseMobile();
    }
  };

  const renderNavContent = () => (
    <div className="p-4 space-y-6 overflow-y-auto flex-1">
      {/* Navigation Category */}
      <div>
        <div className="text-[11px] font-mono-code uppercase font-semibold text-muted px-2 tracking-wider mb-2">
          Research Views
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-left transition-colors text-xs ${
                  isActive
                    ? 'bg-accent text-white font-medium shadow-xs'
                    : 'text-secondary hover:bg-surface-muted hover:text-primary'
                }`}
              >
                <div className="flex items-center space-x-2.5 truncate">
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-muted'}`} />
                  <span className="truncate">{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] font-mono-code px-1.5 py-0.5 rounded font-medium shrink-0 ${
                      isActive
                        ? 'bg-surface text-primary'
                        : 'bg-surface-muted text-secondary'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* System Architecture Metadata Card */}
      <div className="rounded-md border border-default bg-surface-muted/60 p-3 text-xs space-y-2 font-mono-code">
        <div className="flex items-center space-x-1.5 text-secondary font-semibold text-[11px]">
          <Layers className="w-3.5 h-3.5 text-secondary" />
          <span>Architecture State</span>
        </div>
        <div className="space-y-1 text-[11px] text-secondary">
          <div className="flex justify-between">
            <span>Frontend Host:</span>
            <span className="text-secondary">./dashboard</span>
          </div>
          <div className="flex justify-between">
            <span>Python Core:</span>
            <span className="text-emerald-700 dark:text-emerald-400 font-medium">ISOLATED</span>
          </div>
          <div className="flex justify-between">
            <span>Capital Limit:</span>
            <span className="text-secondary font-medium">$0.00</span>
          </div>
          <div className="flex justify-between">
            <span>Order Engine:</span>
            <span className="text-rose-700 dark:text-rose-400 font-medium">DISABLED</span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderFooter = () => (
    <div className="p-4 border-t border-default bg-surface-muted/50 text-[11px] text-secondary space-y-1.5 shrink-0">
      <div className="flex items-center space-x-1.5 text-secondary font-medium font-mono-code">
        <Database className="w-3 h-3 text-muted" />
        <span>EURUSD H4 Dataset</span>
      </div>
      <div className="flex items-center space-x-1.5 text-[10px] text-muted">
        <Lock className="w-3 h-3 text-muted shrink-0" />
        <span>Bi-temporal fail-closed research harness</span>
      </div>
    </div>
  );

  return (
    <>
      {/* 1. Desktop Persistent Sidebar: Flush-left against viewport, sticky below header */}
      <aside className="hidden lg:flex w-64 shrink-0 bg-surface border-r border-default flex-col justify-between sticky top-14 h-[calc(100vh-3.5rem)]">
        {renderNavContent()}
        {renderFooter()}
      </aside>

      {/* 2. Mobile / Tablet Overlay Drawer Navigation */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={onCloseMobile}
            aria-hidden="true"
          />

          {/* Drawer Sheet */}
          <aside className="fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-surface border-r border-default flex flex-col justify-between shadow-xl">
            {/* Drawer Header */}
            <div className="p-4 border-b border-subtle flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="flex items-center justify-center w-7 h-7 rounded bg-accent border border-transparent text-white font-mono-code font-bold text-xs">
                  AC
                </div>
                <div>
                  <div className="text-xs font-semibold text-primary">ACASH Research</div>
                  <div className="text-[10px] text-secondary font-mono-code">Views Navigation</div>
                </div>
              </div>
              <button
                onClick={onCloseMobile}
                className="p-1.5 rounded text-muted hover:text-primary hover:bg-surface-muted transition-colors"
                aria-label="Close navigation"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Nav & Architecture */}
            {renderNavContent()}

            {/* Dataset Footer */}
            {renderFooter()}
          </aside>
        </div>
      )}
    </>
  );
};
