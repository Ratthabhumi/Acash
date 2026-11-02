import React, { useState } from 'react';

// Presentation-only charts for the UPI view. Labels and values are Python decimal strings;
// `fraction` is bar geometry from barFraction() and is never shown as a number.

export type Tone = 'accent' | 'emerald' | 'sky' | 'violet' | 'amber' | 'rose' | 'unknown';

const TONE: Record<Tone, string> = {
  accent: 'bg-accent',
  emerald: 'bg-emerald-500',
  sky: 'bg-sky-500',
  violet: 'bg-violet-500',
  amber: 'bg-amber-500',
  rose: 'bg-rose-500',
  unknown: 'bg-slate-400/60 bg-[repeating-linear-gradient(45deg,transparent,transparent_4px,rgba(255,255,255,0.25)_4px,rgba(255,255,255,0.25)_8px)]',
};

export interface Segment {
  label: string;
  value: string;
  fraction: number;
  tone: Tone;
  note?: string;
}

export const Swatch: React.FC<{ tone: Tone }> = ({ tone }) => (
  <span aria-hidden className={`inline-block w-2.5 h-2.5 rounded-sm shrink-0 ${TONE[tone]}`} />
);

export const ChartCard: React.FC<{
  title: string;
  subtitle?: string;
  table: React.ReactNode;
  children: React.ReactNode;
}> = ({ title, subtitle, table, children }) => {
  const [asTable, setAsTable] = useState(false);
  return (
    <div className="bg-surface border border-default rounded-lg p-4 space-y-3 min-w-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-primary">{title}</h3>
          {subtitle && <p className="text-xs text-secondary mt-0.5">{subtitle}</p>}
        </div>
        <button type="button" onClick={() => setAsTable((v) => !v)} aria-pressed={asTable}
          className="text-[11px] px-2 py-0.5 rounded border border-default text-secondary hover:bg-surface-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent shrink-0">
          {asTable ? 'Chart' : 'Table'}
        </button>
      </div>
      {asTable ? <div className="overflow-x-auto">{table}</div> : children}
    </div>
  );
};

export const StackedBar: React.FC<{ segments: Segment[]; label: string }> = ({ segments, label }) => (
  <div className="space-y-3">
    <div role="img" aria-label={`${label}: ${segments.map((s) => `${s.label} ${s.value}`).join(', ')}`}
      className="flex h-5 w-full rounded-md overflow-hidden bg-surface-muted">
      {segments.filter((s) => s.fraction > 0).map((s) => (
        <div key={s.label} className={`${TONE[s.tone]} h-full`} style={{ width: `${s.fraction * 100}%` }} title={`${s.label}: ${s.value}`} />
      ))}
    </div>
    <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
      {segments.map((s) => (
        <li key={s.label} className="flex items-center gap-2 min-w-0">
          <Swatch tone={s.tone} />
          <span className="text-secondary truncate">{s.label}</span>
          <span className="ml-auto font-mono-code text-primary tabular-nums">{s.value}</span>
          {s.note && <span className="text-muted font-mono-code tabular-nums w-14 text-right">{s.note}</span>}
        </li>
      ))}
    </ul>
  </div>
);

export interface BarRow {
  key: string;
  label: string;
  value: string;
  note?: string;
  fraction: number;
  tone: Tone;
  badge?: React.ReactNode;
}

export const BarList: React.FC<{ rows: BarRow[]; label: string }> = ({ rows, label }) => (
  <ul aria-label={label} className="space-y-2.5">
    {rows.map((r) => (
      <li key={r.key} className="space-y-1">
        <div className="flex items-baseline gap-2 text-xs min-w-0">
          <span className="text-primary truncate" title={r.label}>{r.label}</span>
          {r.badge}
          <span className="ml-auto font-mono-code text-primary tabular-nums whitespace-nowrap">{r.value}</span>
          {r.note && <span className="font-mono-code text-muted tabular-nums w-14 text-right">{r.note}</span>}
        </div>
        <div className="h-2 w-full rounded bg-surface-muted overflow-hidden" aria-hidden>
          <div className={`${TONE[r.tone]} h-full rounded`} style={{ width: `${r.fraction * 100}%` }} />
        </div>
      </li>
    ))}
  </ul>
);

export const SimpleTable: React.FC<{ head: string[]; rows: Array<Array<React.ReactNode>> }> = ({ head, rows }) => (
  <table className="w-full text-xs font-mono-code">
    <thead>
      <tr className="text-left text-muted">
        {head.map((h, i) => <th key={h} className={`py-1 font-medium ${i > 0 ? 'text-right' : ''}`}>{h}</th>)}
      </tr>
    </thead>
    <tbody>
      {rows.map((row, i) => (
        <tr key={i} className="border-t border-subtle">
          {row.map((cell, j) => <td key={j} className={`py-1.5 ${j > 0 ? 'text-right tabular-nums' : 'text-primary'}`}>{cell}</td>)}
        </tr>
      ))}
    </tbody>
  </table>
);
