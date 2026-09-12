import React, { useState, useMemo } from 'react';
import { EquityPoint } from '../../types/research';
import { useTheme } from '../../context/ThemeContext';

interface EquityDrawdownChartProps {
  data: EquityPoint[];
}

type TimeframeOption = '1W' | '1M' | '3M' | 'ALL';

export const EquityDrawdownChart: React.FC<EquityDrawdownChartProps> = ({ data }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [activeTimeframe, setActiveTimeframe] = useState<TimeframeOption>('ALL');
  const [hoveredPoint, setHoveredPoint] = useState<EquityPoint | null>(null);
  const [hoverX, setHoverX] = useState<number | null>(null);

  // Filter data based on selected timeframe
  const filteredData = useMemo(() => {
    if (!data || data.length === 0) return [];
    if (activeTimeframe === '1W') {
      return data.slice(Math.max(0, data.length - 8));
    }
    if (activeTimeframe === '1M') {
      return data.slice(Math.max(0, data.length - 31));
    }
    if (activeTimeframe === '3M' || activeTimeframe === 'ALL') {
      return data;
    }
    return data;
  }, [data, activeTimeframe]);

  // Geometry calculations for SVG
  const width = 900;
  const equityHeight = 220;
  const drawdownHeight = 90;
  const padding = { top: 20, right: 30, bottom: 25, left: 65 };

  const chartWidth = width - padding.left - padding.right;

  const { minEquity, maxEquity, minDrawdown, maxDrawdown } = useMemo(() => {
    if (filteredData.length === 0) {
      return { minEquity: 95000, maxEquity: 105000, minDrawdown: -5, maxDrawdown: 0 };
    }
    let minE = Infinity;
    let maxE = -Infinity;
    let minD = 0;

    filteredData.forEach((d) => {
      const lowVal = Math.min(d.netEquity, d.grossEquity || d.netEquity);
      const highVal = Math.max(d.netEquity, d.grossEquity || d.netEquity);
      if (lowVal < minE) minE = lowVal;
      if (highVal > maxE) maxE = highVal;
      if (d.drawdownPct < minD) minD = d.drawdownPct;
    });

    const equityPad = (maxE - minE) * 0.08 || 1000;
    return {
      minEquity: Math.floor((minE - equityPad) / 1000) * 1000,
      maxEquity: Math.ceil((maxE + equityPad) / 1000) * 1000,
      minDrawdown: Math.min(-1, Math.floor(minD - 0.5)),
      maxDrawdown: 0,
    };
  }, [filteredData]);

  // Scale functions
  const getX = (index: number) => {
    if (filteredData.length <= 1) return padding.left;
    return padding.left + (index / (filteredData.length - 1)) * chartWidth;
  };

  const getEquityY = (val: number) => {
    const range = maxEquity - minEquity || 1;
    return padding.top + (1 - (val - minEquity) / range) * equityHeight;
  };


  // Build SVG Paths
  const { netPath, grossPath, netAreaPath, ddAreaPath, ddLinePath } = useMemo(() => {
    if (filteredData.length === 0) {
      return { netPath: '', grossPath: '', netAreaPath: '', ddAreaPath: '', ddLinePath: '' };
    }

    let net = '';
    let gross = '';
    let ddLine = '';
    let ddArea = '';

    const ddZeroY = padding.top + equityHeight + 35 + (0 - minDrawdown) / (maxDrawdown - minDrawdown || 1) * drawdownHeight;

    filteredData.forEach((d, i) => {
      const x = getX(i);
      const netY = getEquityY(d.netEquity);
      const grossY = getEquityY(d.grossEquity || d.netEquity);
      
      const ddRelativeY = (1 - (d.drawdownPct - minDrawdown) / (maxDrawdown - minDrawdown || 1)) * drawdownHeight;
      const ddY = padding.top + equityHeight + 35 + ddRelativeY;

      if (i === 0) {
        net += `M ${x} ${netY}`;
        gross += `M ${x} ${grossY}`;
        ddLine += `M ${x} ${ddY}`;
        ddArea += `M ${x} ${ddZeroY} L ${x} ${ddY}`;
      } else {
        net += ` L ${x} ${netY}`;
        gross += ` L ${x} ${grossY}`;
        ddLine += ` L ${x} ${ddY}`;
        ddArea += ` L ${x} ${ddY}`;
      }
    });

    const lastX = getX(filteredData.length - 1);
    const firstX = getX(0);
    const bottomEquityY = padding.top + equityHeight;
    const netArea = `${net} L ${lastX} ${bottomEquityY} L ${firstX} ${bottomEquityY} Z`;

    const zeroDdY = padding.top + equityHeight + 35; // 0% drawdown is top of drawdown box
    const ddAreaFinal = `${ddLine} L ${lastX} ${zeroDdY} L ${firstX} ${zeroDdY} Z`;

    return {
      netPath: net,
      grossPath: gross,
      netAreaPath: netArea,
      ddAreaPath: ddAreaFinal,
      ddLinePath: ddLine,
    };
  }, [filteredData, minEquity, maxEquity, minDrawdown, maxDrawdown]);

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const mouseSvgX = ((e.clientX - rect.left) / rect.width) * width;
    
    if (mouseSvgX < padding.left || mouseSvgX > width - padding.right) {
      setHoveredPoint(null);
      setHoverX(null);
      return;
    }

    const relativeX = (mouseSvgX - padding.left) / chartWidth;
    const index = Math.round(relativeX * (filteredData.length - 1));
    if (index >= 0 && index < filteredData.length) {
      setHoveredPoint(filteredData[index]);
      setHoverX(getX(index));
    }
  };

  const handleMouseLeave = () => {
    setHoveredPoint(null);
    setHoverX(null);
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-lg border border-enterprise-border dark:border-slate-800 p-4 shadow-xs transition-colors">
      {/* Chart Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800 mb-3">
        <div>
          <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 tracking-tight">
            Portfolio Valuation & Drawdown Profile
          </h3>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono-code mt-0.5">
            Simulated Reference Notional ($100,000) · Mark-to-Market Valuation Profile
          </p>
        </div>

        {/* Legend and Timeframe Filters */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Legend */}
          <div className="flex items-center space-x-3 text-[11px] font-mono-code text-slate-600 dark:text-slate-400">
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-0.5 bg-slate-900 dark:bg-slate-100 rounded-full" />
              <span>Net Equity</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-0.5 bg-slate-400 dark:bg-slate-500 stroke-dasharray rounded-full" />
              <span>Gross (Pre-Friction)</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-2 h-2 bg-rose-400/40 border border-rose-400 rounded-xs" />
              <span>Drawdown</span>
            </div>
          </div>

          {/* Timeframe Buttons */}
          <div className="flex items-center rounded bg-slate-100 dark:bg-slate-800 p-0.5 border border-slate-200 dark:border-slate-700 text-xs font-mono-code">
            {(['1W', '1M', '3M', 'ALL'] as TimeframeOption[]).map((tf) => (
              <button
                key={tf}
                onClick={() => setActiveTimeframe(tf)}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                  activeTimeframe === tf
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-xs'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div className="relative w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${equityHeight + drawdownHeight + 70}`}
          className="w-full h-auto select-none"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <defs>
            <linearGradient id="netEquityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={isDark ? '#38bdf8' : '#0f172a'} stopOpacity={isDark ? 0.12 : 0.08} />
              <stop offset="100%" stopColor={isDark ? '#38bdf8' : '#0f172a'} stopOpacity={0.0} />
            </linearGradient>
            <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.05" />
              <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.25" />
            </linearGradient>
          </defs>

          {/* Gridlines - Equity */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
            const y = padding.top + pct * equityHeight;
            const val = Math.round(maxEquity - pct * (maxEquity - minEquity));
            return (
              <g key={`egrid-${i}`}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke={isDark ? '#1e293b' : '#f1f5f9'}
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 8}
                  y={y + 3}
                  textAnchor="end"
                  className="text-[10px] fill-slate-400 dark:fill-slate-500 font-mono-code"
                >
                  ${val.toLocaleString()}
                </text>
              </g>
            );
          })}

          {/* Area Fill */}
          <path d={netAreaPath} fill="url(#netEquityGradient)" />

          {/* Gross Equity Line (Dashed) */}
          <path
            d={grossPath}
            fill="none"
            stroke={isDark ? '#64748b' : '#94a3b8'}
            strokeWidth="1.25"
            strokeDasharray="3 3"
          />

          {/* Net Equity Line (High-contrast charcoal in light, crisp slate-50 in dark) */}
          <path
            d={netPath}
            fill="none"
            stroke={isDark ? '#f8fafc' : '#0f172a'}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Divider between Equity and Drawdown */}
          <line
            x1={padding.left}
            y1={padding.top + equityHeight + 20}
            x2={width - padding.right}
            y2={padding.top + equityHeight + 20}
            stroke={isDark ? '#1e293b' : '#e2e8f0'}
            strokeWidth="1"
          />

          {/* Drawdown Section Header */}
          <text
            x={padding.left}
            y={padding.top + equityHeight + 30}
            className="text-[10px] font-mono-code fill-slate-500 dark:fill-slate-400 font-medium"
          >
            Drawdown (%)
          </text>

          {/* Drawdown Gridlines */}
          {[0, 0.5, 1].map((pct, i) => {
            const y = padding.top + equityHeight + 35 + pct * drawdownHeight;
            const val = (maxDrawdown - pct * (maxDrawdown - minDrawdown)).toFixed(1);
            return (
              <g key={`dgrid-${i}`}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke={isDark ? '#1e293b' : '#f8fafc'}
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 8}
                  y={y + 3}
                  textAnchor="end"
                  className="text-[10px] fill-slate-400 dark:fill-slate-500 font-mono-code"
                >
                  {val}%
                </text>
              </g>
            );
          })}

          {/* Drawdown Area Fill */}
          <path d={ddAreaPath} fill="url(#drawdownGradient)" />

          {/* Drawdown Line */}
          <path
            d={ddLinePath}
            fill="none"
            stroke="#f43f5e"
            strokeWidth="1.5"
            strokeLinecap="round"
          />

          {/* X Axis Labels (Dates) */}
          {filteredData.map((d, i) => {
            const step = Math.ceil(filteredData.length / 6);
            if (i % step !== 0 && i !== filteredData.length - 1) return null;
            const x = getX(i);
            const y = padding.top + equityHeight + 35 + drawdownHeight + 15;
            return (
              <text
                key={`xlabel-${i}`}
                x={x}
                y={y}
                textAnchor="middle"
                className="text-[10px] fill-slate-400 dark:fill-slate-500 font-mono-code"
              >
                {d.date.slice(5)}
              </text>
            );
          })}

          {/* Crosshair on Hover */}
          {hoverX !== null && (
            <g>
              <line
                x1={hoverX}
                y1={padding.top}
                x2={hoverX}
                y2={padding.top + equityHeight + 35 + drawdownHeight}
                stroke={isDark ? '#475569' : '#64748b'}
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              {hoveredPoint && (
                <>
                  <circle
                    cx={hoverX}
                    cy={getEquityY(hoveredPoint.netEquity)}
                    r="3.5"
                    fill={isDark ? '#f8fafc' : '#0f172a'}
                    stroke={isDark ? '#0f172a' : '#ffffff'}
                    strokeWidth="1.5"
                  />
                  <circle
                    cx={hoverX}
                    cy={
                      padding.top +
                      equityHeight +
                      35 +
                      (1 -
                        (hoveredPoint.drawdownPct - minDrawdown) /
                          (maxDrawdown - minDrawdown || 1)) *
                        drawdownHeight
                    }
                    r="3"
                    fill="#f43f5e"
                    stroke={isDark ? '#0f172a' : '#ffffff'}
                    strokeWidth="1.5"
                  />
                </>
              )}
            </g>
          )}
        </svg>

        {/* Hover Tooltip Box */}
        {hoveredPoint && hoverX !== null && (
          <div
            className="absolute top-4 pointer-events-none bg-slate-900/95 text-white border border-slate-700/80 rounded-md p-2.5 text-xs shadow-lg backdrop-blur-xs font-mono-code z-20 space-y-1"
            style={{
              left: `${Math.min(
                Math.max(10, (hoverX / width) * 100),
                70
              )}%`,
            }}
          >
            <div className="text-[10px] text-slate-400 border-b border-slate-800 pb-1 flex justify-between gap-4">
              <span>Day {hoveredPoint.index}</span>
              <span className="text-slate-300 font-semibold">{hoveredPoint.date}</span>
            </div>
            <div className="flex justify-between gap-4 text-[11px]">
              <span className="text-slate-400">Simulated Notional:</span>
              <span className="font-semibold text-emerald-400">
                ${hoveredPoint.netEquity.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between gap-4 text-[11px]">
              <span className="text-slate-400">Gross (Pre-Friction):</span>
              <span className="text-slate-300">
                ${hoveredPoint.grossEquity?.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between gap-4 text-[11px]">
              <span className="text-slate-400">Drawdown:</span>
              <span
                className={`font-semibold ${
                  hoveredPoint.drawdownPct < 0 ? 'text-rose-400' : 'text-slate-300'
                }`}
              >
                {hoveredPoint.drawdownPct.toFixed(2)}%
              </span>
            </div>
            <div className="flex justify-between gap-4 text-[11px] pt-1 border-t border-slate-800/80 text-[10px]">
              <span className="text-slate-400">Simulated Fills:</span>
              <span className="text-slate-200">{hoveredPoint.tradeCount}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
