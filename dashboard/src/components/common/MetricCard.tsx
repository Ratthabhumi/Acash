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
  let trendClass = 'text-secondary';
  if (trend === 'up') trendClass = 'text-emerald-700 dark:text-emerald-400 font-medium';
  if (trend === 'down') trendClass = 'text-rose-700 dark:text-rose-400 font-medium';

  return (
    <div className={`bg-surface border border-default rounded-md p-4 flex flex-col justify-between transition-shadow hover:shadow-sm ${className}`}>
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-medium uppercase tracking-wider text-secondary truncate">
          {label}
        </span>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {badge}
          {icon && <div className="text-muted">{icon}</div>}
        </div>
      </div>
      <div>
        <div className="text-2xl font-semibold tracking-tight text-primary font-mono-code">
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
