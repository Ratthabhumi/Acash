import React from 'react';
import { Database, AlertCircle } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  message?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Research Runs Found',
  message = 'Research runs will appear here once an authorized quantitative research process produces a verified run manifest artifact.',
  icon,
  action,
}) => {
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md p-10 text-center flex flex-col items-center justify-center max-w-lg mx-auto my-8 transition-colors">
      <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 dark:text-slate-500 mb-4">
        {icon || <Database className="w-6 h-6" />}
      </div>
      <h3 className="text-base font-semibold text-charcoal-900 dark:text-slate-100 mb-1.5">{title}</h3>
      <p className="text-xs text-charcoal-500 dark:text-slate-400 leading-relaxed max-w-md mb-4">{message}</p>
      <div className="inline-flex items-center gap-1.5 text-[11px] text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded px-2.5 py-1 mb-4">
        <AlertCircle className="w-3.5 h-3.5" />
        <span>Strict Invariant: System requires bit-for-bit sealed manifest lineage.</span>
      </div>
      {action}
    </div>
  );
};
