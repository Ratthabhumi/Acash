import React from 'react';
import { 
  BarChart3, 
  ArrowLeftRight, 
  GitBranch, 
  ShieldCheck, 
  Database,
  Lock,
  Layers
} from 'lucide-react';

export type DashboardTab = 'overview' | 'trades' | 'evidence' | 'validation';

interface SidebarProps {
  currentTab: DashboardTab;
  onSelectTab: (tab: DashboardTab) => void;
  tradeCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, tradeCount }) => {
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
  ];

  return (
    <aside className="w-64 shrink-0 bg-white border-r border-enterprise-border flex flex-col justify-between h-[calc(100vh-85px)] sticky top-[85px]">
      <div className="p-4 space-y-6 overflow-y-auto">
        {/* Navigation Category */}
        <div>
          <div className="text-[11px] font-mono-code uppercase font-semibold text-slate-400 px-2 tracking-wider mb-2">
            Research Views
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-left transition-colors text-xs ${
                    isActive
                      ? 'bg-slate-900 text-white font-medium shadow-xs'
                      : 'text-slate-700 hover:bg-slate-100/80 hover:text-slate-900'
                  }`}
                >
                  <div className="flex items-center space-x-2.5 truncate">
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                    <span className="truncate">{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[10px] font-mono-code px-1.5 py-0.5 rounded font-medium shrink-0 ${
                        isActive
                          ? 'bg-slate-800 text-slate-300'
                          : 'bg-slate-100 text-slate-600'
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
        <div className="rounded-md border border-slate-200 bg-slate-50/60 p-3 text-xs space-y-2 font-mono-code">
          <div className="flex items-center space-x-1.5 text-slate-700 font-semibold text-[11px]">
            <Layers className="w-3.5 h-3.5 text-slate-500" />
            <span>Architecture State</span>
          </div>
          <div className="space-y-1 text-[11px] text-slate-500">
            <div className="flex justify-between">
              <span>Frontend Host:</span>
              <span className="text-slate-700">./dashboard</span>
            </div>
            <div className="flex justify-between">
              <span>Python Core:</span>
              <span className="text-emerald-700 font-medium">ISOLATED</span>
            </div>
            <div className="flex justify-between">
              <span>Capital Limit:</span>
              <span className="text-slate-700 font-medium">$0.00</span>
            </div>
            <div className="flex justify-between">
              <span>Order Engine:</span>
              <span className="text-rose-700 font-medium">DISABLED</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer System Notice */}
      <div className="p-4 border-t border-enterprise-border bg-slate-50/50 text-[11px] text-slate-500 space-y-1.5">
        <div className="flex items-center space-x-1.5 text-slate-700 font-medium font-mono-code">
          <Database className="w-3 h-3 text-slate-400" />
          <span>EURUSD H4 Dataset</span>
        </div>
        <div className="flex items-center space-x-1.5 text-[10px] text-slate-400">
          <Lock className="w-3 h-3 text-slate-400 shrink-0" />
          <span>Bi-temporal fail-closed research harness</span>
        </div>
      </div>
    </aside>
  );
};
