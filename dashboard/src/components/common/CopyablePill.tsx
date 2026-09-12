import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface CopyablePillProps {
  label?: string;
  value: string;
  truncateLength?: number;
  className?: string;
}

export const CopyablePill: React.FC<CopyablePillProps> = ({
  label,
  value,
  truncateLength = 12,
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Fallback
      setCopied(false);
    }
  };

  const displayValue = truncateLength && value.length > truncateLength * 2
    ? `${value.slice(0, truncateLength)}...${value.slice(-truncateLength)}`
    : value;

  return (
    <div className={`inline-flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded px-2 py-0.5 text-xs text-charcoal-700 font-mono-code transition-colors hover:border-slate-300 ${className}`}>
      {label && <span className="text-slate-400 select-none font-sans font-normal">{label}:</span>}
      <span className="truncate max-w-[220px]" title={value}>
        {displayValue}
      </span>
      <button
        onClick={handleCopy}
        type="button"
        title={copied ? 'Copied to clipboard' : 'Click to copy full value'}
        className="text-slate-400 hover:text-slate-700 focus:outline-none flex items-center gap-1 ml-0.5"
      >
        {copied ? (
          <span className="inline-flex items-center text-[10px] text-emerald-700 font-sans font-medium">
            <Check className="w-3 h-3 mr-0.5" />
            Copied
          </span>
        ) : (
          <Copy className="w-3 h-3" />
        )}
      </button>
    </div>
  );
};
