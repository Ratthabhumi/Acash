import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  badge?: React.ReactNode;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subValue,
  badge,
  icon,
  trend,
  className = '',
}) => {
  let trendClass = 'text-charcoal-500 dark:text-slate-400';
  if (trend === 'up') trendClass = 'text-emerald-700 dark:text-emerald-400 font-medium';
  if (trend === 'down') trendClass = 'text-rose-700 dark:text-rose-400 font-medium';

  return (
    <div className={`bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md p-4 flex flex-col justify-between transition-shadow hover:shadow-sm ${className}`}>
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400 truncate">
          {label}
        </span>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {badge}
          {icon && <div className="text-slate-400 dark:text-slate-500">{icon}</div>}
        </div>
      </div>
      <div>
        <div className="text-2xl font-semibold tracking-tight text-charcoal-900 dark:text-slate-100 font-mono-code">
          {value}
        </div>
        {subValue && (
          <div className={`text-xs mt-1 truncate ${trendClass}`}>
            {subValue}
          </div>
        )}
      </div>
    </div>
  );
};
