import React, { useState, useEffect } from 'react';
import { ResearchRun } from './types/research';
import { researchRunRepository } from './services/researchRepository';
import { AppShell } from './components/layout/AppShell';
import { DashboardTab } from './components/layout/Sidebar';
import { OverviewPage } from './pages/OverviewPage';
import { TradesPage } from './pages/TradesPage';
import { EvidencePage } from './pages/EvidencePage';
import { ValidationPage } from './pages/ValidationPage';
import { SkeletonLoader } from './components/common/SkeletonLoader';
import { ThemeProvider } from './context/ThemeContext';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<DashboardTab>('overview');
  const [researchRun, setResearchRun] = useState<ResearchRun | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedTradeId, setSelectedTradeId] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const run = await researchRunRepository.getLatestRun();
        setResearchRun(run);
      } catch (err) {
        console.error('Failed to load research run data', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading || !researchRun) {
    return (
      <div className="min-h-screen w-full bg-slate-50 dark:bg-slate-950">
        <div className="p-8 flex flex-col space-y-4 max-w-6xl mx-auto">
          <SkeletonLoader className="h-10 w-full" />
          <SkeletonLoader className="h-16 w-full" />
          <div className="grid grid-cols-4 gap-4">
            <SkeletonLoader className="h-24" />
            <SkeletonLoader className="h-24" />
            <SkeletonLoader className="h-24" />
            <SkeletonLoader className="h-24" />
          </div>
          <SkeletonLoader className="h-96 w-full" />
        </div>
      </div>
    );
  }

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
        {currentTab === 'overview' && (
          <OverviewPage
            researchRun={researchRun}
            onNavigateTab={handleNavigateTab}
            onSelectTradeId={handleSelectTrade}
          />
        )}

        {currentTab === 'trades' && (
          <TradesPage
            trades={researchRun.trades}
            initialSelectedTradeId={selectedTradeId}
          />
        )}

        {currentTab === 'evidence' && (
          <EvidencePage researchRun={researchRun} />
        )}

        {currentTab === 'validation' && (
          <ValidationPage researchRun={researchRun} />
        )}
      </AppShell>
    </ThemeProvider>
  );
};

export default App;
