import React, { useState, useEffect } from 'react';
import { ResearchRun } from './types/research';
import { researchRunRepository } from './services/researchRepository';
import { AppShell } from './components/layout/AppShell';
import { DashboardTab } from './components/layout/Sidebar';
import { OverviewPage } from './pages/OverviewPage';
import { TradesPage } from './pages/TradesPage';
import { EvidencePage } from './pages/EvidencePage';
import { ValidationPage } from './pages/ValidationPage';
import { ShadowTournamentPage } from './pages/ShadowTournamentPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { SkeletonLoader } from './components/common/SkeletonLoader';
import { ThemeProvider } from './context/ThemeContext';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<DashboardTab>(window.location.hash === '#portfolio' ? 'portfolio' : 'overview');
  const [researchRun, setResearchRun] = useState<ResearchRun | null>(null);
  const [researchState, setResearchState] = useState<'LOADING' | 'READY' | 'SERVICE_UNAVAILABLE'>('LOADING');
  const [selectedTradeId, setSelectedTradeId] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const run = await researchRunRepository.getLatestRun();
        setResearchRun(run);
        setResearchState('READY');
      } catch (err) {
        console.error('Failed to load research run data', err);
        setResearchState('SERVICE_UNAVAILABLE');
      }
    }
    loadData();
  }, []);

  const researchPlaceholder = researchState === 'LOADING' ? (
    <div className="flex flex-col space-y-4 max-w-6xl">
      <SkeletonLoader className="h-16 w-full" />
      <div className="grid grid-cols-4 gap-4">
        <SkeletonLoader className="h-24" />
        <SkeletonLoader className="h-24" />
        <SkeletonLoader className="h-24" />
        <SkeletonLoader className="h-24" />
      </div>
      <SkeletonLoader className="h-96 w-full" />
    </div>
  ) : (
    <div className="bg-surface border border-default rounded-md p-6 text-sm text-secondary">
      RESEARCH RUN UNAVAILABLE · the research workspace could not be loaded; portfolio views are unaffected.
    </div>
  );

  const handleNavigateTab = (tab: DashboardTab) => {
    setCurrentTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectTrade = (tradeId: string) => {
    setSelectedTradeId(tradeId);
    setCurrentTab('trades');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <ThemeProvider>
      <AppShell
        researchRun={researchRun}
        currentTab={currentTab}
        onSelectTab={handleNavigateTab}
      >
        {currentTab === 'portfolio' && <PortfolioPage />}

        {['overview', 'trades', 'evidence', 'validation'].includes(currentTab) && !researchRun && researchPlaceholder}

        {currentTab === 'overview' && researchRun && (
          <OverviewPage
            researchRun={researchRun}
            onNavigateTab={handleNavigateTab}
            onSelectTradeId={handleSelectTrade}
          />
        )}

        {currentTab === 'trades' && researchRun && (
          <TradesPage
            trades={researchRun.trades}
            initialSelectedTradeId={selectedTradeId}
          />
        )}

        {currentTab === 'evidence' && researchRun && (
          <EvidencePage researchRun={researchRun} />
        )}

        {currentTab === 'validation' && researchRun && (
          <ValidationPage researchRun={researchRun} />
        )}

        {currentTab === 'shadow' && (
          <ShadowTournamentPage />
        )}
      </AppShell>
    </ThemeProvider>
  );
};

export default App;
