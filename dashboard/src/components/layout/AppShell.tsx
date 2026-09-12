import React, { useState, useEffect } from 'react';
import { Header } from './Header';
import { Sidebar, DashboardTab } from './Sidebar';
import { CommandPalette } from './CommandPalette';
import { ResearchRun } from '../../types/research';

interface AppShellProps {
  researchRun: ResearchRun;
  currentTab: DashboardTab;
  onSelectTab: (tab: DashboardTab) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  researchRun,
  currentTab,
  onSelectTab,
  children,
}) => {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  return (
    <div className="min-h-screen w-full bg-slate-50 dark:bg-slate-950 flex flex-col font-sans text-slate-800 dark:text-slate-100 antialiased selection:bg-slate-200 dark:selection:bg-slate-800">
      {/* 1. Primary Header */}
      <Header
        metadata={researchRun.metadata}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        isMobileMenuOpen={isMobileMenuOpen}
        onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)}
      />

      {/* 2. Main Workspace Area: Full viewport width, flush-left sidebar */}
      <div className="flex-1 flex w-full min-h-0">
        {/* Left Navigation Sidebar */}
        <Sidebar
          currentTab={currentTab}
          onSelectTab={onSelectTab}
          tradeCount={researchRun.metadata.totalTradeCount}
          isMobileOpen={isMobileMenuOpen}
          onCloseMobile={() => setIsMobileMenuOpen(false)}
        />

        {/* Dynamic Content Pane: Expands into all available width */}
        <main className="flex-1 min-w-0 p-4 lg:p-6 overflow-x-hidden bg-slate-50 dark:bg-slate-950">
          {children}
        </main>
      </div>

      {/* 3. Keyboard Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectTab={onSelectTab}
      />
    </div>
  );
};
