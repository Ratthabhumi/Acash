import React from 'react';

export interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ 
  status, 
  size = 'sm',
  className = '' 
}) => {
  const norm = status.toUpperCase().replace(/\s+/g, '_');

  let bgClass = 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700';

  if (norm === 'NOT_AUTHORIZED' || norm === 'FAIL' || norm === 'CLOSED_LOSS' || norm === 'REJECTED') {
    bgClass = 'bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 border-rose-200 dark:border-rose-800/60';
  } else if (norm === 'PASS' || norm === 'CLOSED_WIN' || norm === 'COMPLETED') {
    bgClass = 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/60';
  } else if (norm === 'PENDING' || norm === 'PENDING_REVIEW' || norm === 'WARNING') {
    bgClass = 'bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-800/60';
  } else if (norm === 'DEMO' || norm === 'DEMO_DATA' || norm === 'INFO') {
    bgClass = 'bg-blue-50 dark:bg-blue-950/40 text-blue-800 dark:text-blue-300 border-blue-200 dark:border-blue-800/60';
  } else if (norm === 'NOT_EVALUATED' || norm === 'NOT_APPLICABLE') {
    bgClass = 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-300 dark:border-slate-700';
  }

  const sizeClass = size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1';

  return (
    <span
      className={`inline-flex items-center font-medium rounded border tracking-wide font-mono-code ${sizeClass} ${bgClass} ${className}`}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
};
