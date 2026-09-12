import React from 'react';

export const SkeletonLoader: React.FC<{ rows?: number; height?: string; className?: string }> = ({
  rows = 4,
  height = 'h-6',
  className = '',
}) => {
  return (
    <div className={`animate-pulse space-y-3 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={`bg-slate-200 dark:bg-slate-800 rounded ${height}`}
          style={{ opacity: 1 - i * (0.6 / rows) }}
        />
      ))}
    </div>
  );
};
