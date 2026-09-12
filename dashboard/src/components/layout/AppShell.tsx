import React, { useState, useEffect } from 'react';
import { GovernanceBanner } from './GovernanceBanner';
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
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-800 antialiased selection:bg-slate-200">
      {/* 1. Epistemic Warning Banner */}
      <GovernanceBanner
        demoNotice={researchRun.metadata.demoNotice}
        disclaimer={researchRun.metadata.governanceDisclaimer}
      />

      {/* 2. Primary Header */}
      <Header
        metadata={researchRun.metadata}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
      />

      {/* 3. Main Workspace Area */}
      <div className="flex-1 flex flex-col lg:flex-row w-full max-w-[1600px] mx-auto">
        {/* Left Navigation Sidebar */}
        <Sidebar
          currentTab={currentTab}
          onSelectTab={onSelectTab}
          tradeCount={researchRun.metadata.totalTradeCount}
        />

        {/* Dynamic Content Pane */}
        <main className="flex-1 p-4 lg:p-6 overflow-x-hidden min-h-[calc(100vh-130px)]">
          {children}
        </main>
      </div>

      {/* 4. Keyboard Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectTab={onSelectTab}
      />
    </div>
  );
};
