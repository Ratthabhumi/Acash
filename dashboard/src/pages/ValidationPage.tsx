import React from 'react';
import { ShieldAlert, Lock, Info } from 'lucide-react';
import { ResearchRun } from '../types/research';
import { StatusBadge } from '../components/common/StatusBadge';

interface ValidationPageProps {
  researchRun: ResearchRun;
}

export const ValidationPage: React.FC<ValidationPageProps> = ({ researchRun }) => {
  const { validationCriteria, oosComparison, metadata } = researchRun;

  return (
    <div className="space-y-6">
      {/* 1. Human Authorization Gate Status (Non-Negotiable Governance Banner) */}
      <div className="rounded-lg border-2 border-rose-500/30 bg-rose-50/50 p-4 sm:p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0" />
              <h2 className="text-sm font-semibold font-mono-code text-rose-950 uppercase tracking-wide">
                Human Research Authorization: {metadata.humanAuthorizationStatus.replace('_', ' ')}
              </h2>
            </div>
            <p className="text-xs text-rose-900/80 font-sans leading-relaxed">
              This strategy (<span className="font-mono-code font-semibold">{metadata.strategyId}</span>) has not been ratified for production or execution. Trading authority remains strictly locked at <span className="font-mono-code font-semibold">$0.00</span>.
            </p>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <span className="px-3 py-1 rounded bg-rose-600 text-white font-mono-code font-bold text-xs shadow-xs">
              LOCKED · $0.00
            </span>
          </div>
        </div>

        {/* Runtime Invariant Clarification */}
        <div className="mt-3 pt-3 border-t border-rose-200/60 flex flex-col sm:flex-row sm:items-center justify-between text-[11px] font-mono-code text-rose-800 gap-2">
          <div className="flex items-center space-x-1.5">
            <Lock className="w-3.5 h-3.5 text-rose-700 shrink-0" />
            <span>NO_REAL_ORDERS=true is strictly enforced by ACASH execution/runtime layer.</span>
          </div>
          <span className="text-rose-700/80">Dashboard has zero order/execution capability.</span>
        </div>
      </div>

      {/* 2. Statistical Criteria Audit Matrix */}
      <div className="bg-white rounded-lg border border-enterprise-border p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-xs font-semibold text-slate-900 tracking-tight">
              Multi-Gate Statistical Audit Criteria
            </h3>
            <p className="text-[11px] text-slate-500 font-mono-code mt-0.5">
              Strict fail-closed checks · Evaluated without artificial floors or silent fallbacks
            </p>
          </div>

          <div className="text-[11px] font-mono-code px-2 py-0.5 rounded bg-slate-100 text-slate-600">
            {validationCriteria.length} Defined Verification Gates
          </div>
        </div>

        {/* Criteria Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono-code">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-[11px]">
                <th className="pb-2 font-medium">Gate ID</th>
                <th className="pb-2 font-medium">Criterion & Specification</th>
                <th className="pb-2 font-medium">Observed Value</th>
                <th className="pb-2 font-medium">Audit Notes</th>
                <th className="pb-2 font-medium text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {validationCriteria.map((crit) => (
                <tr key={crit.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 font-semibold text-slate-900 whitespace-nowrap">{crit.id}</td>
                  <td className="py-3 pr-4 max-w-xs">
                    <div className="font-semibold text-slate-800">{crit.name}</div>
                    <div className="text-[11px] text-slate-500 font-sans mt-0.5">
                      {crit.ruleSpecification}
                    </div>
                  </td>
                  <td className="py-3 text-slate-700 text-[11px] whitespace-nowrap">
                    {crit.observedMetric}
                  </td>
                  <td className="py-3 text-[11px] text-slate-500 font-sans max-w-xs">
                    {crit.notes}
                  </td>
                  <td className="py-3 text-center whitespace-nowrap">
                    <StatusBadge status={crit.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. In-Sample vs Out-of-Sample (OOS) Partition Separation */}
      <div className="bg-white rounded-lg border border-enterprise-border p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-xs font-semibold text-slate-900 tracking-tight">
                In-Sample vs. Blind Out-of-Sample (OOS) Isolation
              </h3>
              <span className="text-[10px] font-mono-code px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-medium">
                Pristine Partition Policy
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-mono-code mt-0.5">
              Strict isolation preventing p-hacking, multi-testing snooping, and hindsight bias
            </p>
          </div>

          <div className="flex items-center space-x-1.5 text-xs font-mono-code text-slate-600 bg-slate-50 px-2.5 py-1 rounded border border-slate-200">
            <Lock className="w-3 h-3 text-slate-500" />
            <span>DEMO OOS PARTITION · SIMULATED</span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono-code">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-[11px]">
                <th className="pb-2 font-medium">Evaluation Metric</th>
                <th className="pb-2 font-medium text-right">In-Sample (Simulated)</th>
                <th className="pb-2 font-medium text-right">Out-of-Sample (Demo Partition)</th>
                <th className="pb-2 font-medium text-right">Degradation Delta</th>
                <th className="pb-2 font-medium text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {oosComparison.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-2.5 font-medium text-slate-800">{row.metricName}</td>
                  <td className="py-2.5 text-right text-slate-700">{row.inSampleValue}</td>
                  <td className="py-2.5 text-right font-semibold text-slate-500">{row.outOfSampleValue}</td>
                  <td className="py-2.5 text-right text-slate-400">{row.delta}</td>
                  <td className="py-2.5 text-center">
                    <StatusBadge status={row.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-[11px] font-mono-code text-slate-600 space-y-1">
          <div className="flex items-center space-x-1.5 font-semibold text-slate-800">
            <Info className="w-3.5 h-3.5 text-slate-500" />
            <span>Epistemic Integrity Notice:</span>
          </div>
          <p className="leading-relaxed font-sans text-slate-600">
            Mock Demonstration Notice: In canonical ACASH governance, out-of-sample partitions remain strictly unexposed during active research iterations. The partitions shown in this dashboard are purely synthetic mock structures and do not represent actual ACASH research evidence or qualification.
          </p>
        </div>
      </div>
    </div>
  );
};
