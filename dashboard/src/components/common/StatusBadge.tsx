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

  let bgClass = 'bg-slate-100 text-slate-700 border-slate-200';

  if (norm === 'NOT_AUTHORIZED' || norm === 'FAIL' || norm === 'CLOSED_LOSS' || norm === 'REJECTED') {
    bgClass = 'bg-rose-50 text-rose-800 border-rose-200';
  } else if (norm === 'PASS' || norm === 'CLOSED_WIN' || norm === 'COMPLETED') {
    bgClass = 'bg-emerald-50 text-emerald-800 border-emerald-200';
  } else if (norm === 'PENDING' || norm === 'PENDING_REVIEW' || norm === 'WARNING') {
    bgClass = 'bg-amber-50 text-amber-800 border-amber-200';
  } else if (norm === 'DEMO' || norm === 'DEMO_DATA' || norm === 'INFO') {
    bgClass = 'bg-blue-50 text-blue-800 border-blue-200';
  } else if (norm === 'NOT_EVALUATED' || norm === 'NOT_APPLICABLE') {
    bgClass = 'bg-slate-100 text-slate-600 border-slate-300';
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
