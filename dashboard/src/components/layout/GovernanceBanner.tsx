import React from 'react';
import { AlertTriangle, ShieldAlert } from 'lucide-react';

interface GovernanceBannerProps {
  demoNotice?: string;
  disclaimer?: string;
}

export const GovernanceBanner: React.FC<GovernanceBannerProps> = ({
  demoNotice = 'DEMO DATA · SIMULATED RESEARCH RUN · NOT ACASH RESEARCH EVIDENCE',
  disclaimer = 'Performance metrics do not imply research qualification or trading authorization.',
}) => {
  return (
    <aside aria-label="Governance and Data Lineage Warning" className="w-full bg-amber-500/10 border-b border-amber-500/20 px-4 py-2 text-xs text-amber-900 flex flex-wrap items-center justify-between gap-2 shadow-xs transition-colors">
      <div className="flex items-center space-x-2 font-mono-code font-semibold tracking-wide text-amber-950">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
        <span>{demoNotice}</span>
      </div>
      <div className="flex items-center space-x-2 text-amber-900/90 text-[11px]">
        <ShieldAlert className="w-3.5 h-3.5 text-amber-700 shrink-0" />
        <span>{disclaimer}</span>
      </div>
    </aside>
  );
};
