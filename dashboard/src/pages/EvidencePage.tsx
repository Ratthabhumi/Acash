import React, { useState } from 'react';
import { ArrowRight, FileCode, Database } from 'lucide-react';
import { ResearchRun, LineageNode } from '../types/research';
import { CopyablePill } from '../components/common/CopyablePill';

interface EvidencePageProps {
  researchRun: ResearchRun;
}

export const EvidencePage: React.FC<EvidencePageProps> = ({ researchRun }) => {
  const { lineage, dataset, config, metadata } = researchRun;
  const [selectedNode, setSelectedNode] = useState<LineageNode>(lineage[0]);

  return (
    <div className="space-y-6">
      {/* 1. Page Header & Epistemic Authority Statement */}
      <div className="bg-white dark:bg-slate-900 rounded-lg border border-enterprise-border dark:border-slate-800 p-4 shadow-xs transition-colors">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 tracking-tight">
                Causal Evidence Lineage DAG
              </h2>
              <span className="text-xs font-mono-code px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium">
                11 Canonical Stages
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-mono-code mt-0.5">
              Strict unidirectional causal progression from raw immutable ticks to final governance manifest
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <CopyablePill label="Final Manifest" value={metadata.manifestHash} truncateLength={10} />
          </div>
        </div>
      </div>

      {/* 2. Interactive 11-Stage Visual DAG Stepper */}
      <div className="bg-white dark:bg-slate-900 rounded-lg border border-enterprise-border dark:border-slate-800 p-4 shadow-xs space-y-3 transition-colors">
        <div className="text-xs font-mono-code font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
          Sequential Pipeline Graph (Click node to inspect cryptographic proofs)
        </div>

        {/* Responsive Horizontal / Grid DAG Nodes */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-11 gap-2 pt-2">
          {lineage.map((node, index) => {
            const isSelected = selectedNode.id === node.id;
            return (
              <div
                key={node.id}
                onClick={() => setSelectedNode(node)}
                className={`relative cursor-pointer rounded border p-2.5 transition-all text-left flex flex-col justify-between min-h-[90px] ${
                  isSelected
                    ? 'border-slate-900 dark:border-slate-400 bg-slate-900 dark:bg-slate-800 text-white shadow-xs'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-400 dark:hover:border-slate-700 hover:bg-slate-50/80 dark:hover:bg-slate-800/60 text-slate-800 dark:text-slate-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`text-[10px] font-mono-code font-bold px-1.5 py-0.5 rounded ${
                      isSelected ? 'bg-slate-800 dark:bg-slate-700 text-slate-200' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    #{node.stageNumber}
                  </span>
                  {index < lineage.length - 1 && (
                    <ArrowRight className={`hidden xl:block w-3 h-3 ${isSelected ? 'text-slate-400' : 'text-slate-300 dark:text-slate-600'} -mr-1`} />
                  )}
                </div>

                <div className="my-1">
                  <div className={`text-xs font-semibold leading-tight truncate ${isSelected ? 'text-white' : 'text-slate-900 dark:text-slate-100'}`}>
                    {node.stageName}
                  </div>
                  <div className={`text-[10px] font-mono-code truncate mt-0.5 ${isSelected ? 'text-slate-300' : 'text-slate-500 dark:text-slate-400'}`}>
                    {node.shortTitle}
                  </div>
                </div>

                <div className={`text-[9px] font-mono-code truncate ${isSelected ? 'text-slate-400' : 'text-slate-400 dark:text-slate-500'}`}>
                  {node.artifactName}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Selected Stage Deep-Dive Inspection Panel */}
      {selectedNode && (
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-enterprise-border dark:border-slate-800 p-5 shadow-xs space-y-4 transition-colors">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono-code text-xs font-bold px-2 py-0.5 rounded bg-slate-900 dark:bg-slate-800 text-white dark:text-slate-200 border border-slate-700">
                  Stage {selectedNode.stageNumber} of 11
                </span>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {selectedNode.stageName}: {selectedNode.shortTitle}
                </h3>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300 font-sans mt-1">
                {selectedNode.description}
              </p>
            </div>

            <CopyablePill label="Digest" value={selectedNode.hashOrDigest} truncateLength={14} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono-code text-xs">
            {/* Metadata Block 1 */}
            <div className="p-3 rounded bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 space-y-1.5">
              <div className="text-[11px] text-slate-500 dark:text-slate-400">Authority Rule Contract</div>
              <div className="font-semibold text-slate-900 dark:text-slate-200 text-xs truncate">
                {selectedNode.authorityRule}
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 pt-1">Python Source Module</div>
              <div className="text-slate-700 dark:text-slate-300 text-xs truncate">{selectedNode.sourceModule}</div>
            </div>

            {/* Metadata Block 2 */}
            <div className="p-3 rounded bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 space-y-1.5">
              <div className="text-[11px] text-slate-500 dark:text-slate-400">Sealed Artifact</div>
              <div className="font-semibold text-slate-900 dark:text-slate-200 text-xs truncate">
                {selectedNode.artifactName}
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 pt-1">Timestamp (UTC)</div>
              <div className="text-slate-700 dark:text-slate-300 text-xs truncate">{selectedNode.timestamp}</div>
            </div>

            {/* Metadata Block 3: Lineage Connections */}
            <div className="p-3 rounded bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 space-y-1.5">
              <div className="text-[11px] text-slate-500 dark:text-slate-400">Upstream Origin</div>
              <div className="text-slate-800 dark:text-slate-200 text-xs truncate">
                {selectedNode.inputLineage.join(', ') || 'Root Genesis'}
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 pt-1">Downstream Consumer</div>
              <div className="text-slate-800 dark:text-slate-200 text-xs truncate">
                {selectedNode.outputLineage.join(', ') || 'Terminal Manifest'}
              </div>
            </div>
          </div>

          {/* Raw Structured Evidence Payload */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono-code text-slate-600 dark:text-slate-300">
              <span className="font-semibold">Recorded Stage Evidence Payload (JSON)</span>
              <span className="text-[11px] text-slate-400 dark:text-slate-500">Cryptographically immutable state</span>
            </div>
            <pre className="p-3 rounded bg-slate-900 dark:bg-slate-950 text-slate-100 dark:text-slate-200 font-mono-code text-xs overflow-x-auto border border-slate-800 dark:border-slate-800">
              {JSON.stringify(selectedNode.mockEvidencePayload, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* 4. Dataset & Configuration Cryptographic Proofs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dataset Origin Proof */}
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-enterprise-border dark:border-slate-800 p-4 shadow-xs space-y-3 font-mono-code text-xs transition-colors">
          <div className="flex items-center space-x-2 border-b border-slate-100 dark:border-slate-800 pb-2">
            <Database className="w-4 h-4 text-slate-500 dark:text-slate-400" />
            <h4 className="font-semibold text-slate-900 dark:text-slate-100">Dataset Lineage & Verification</h4>
          </div>
          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Dataset ID:</span>
              <span className="text-slate-800 dark:text-slate-200">{dataset.datasetId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Storage Engine:</span>
              <span className="text-slate-800 dark:text-slate-200">{dataset.storageEngine}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Bar Count:</span>
              <span className="text-slate-800 dark:text-slate-200">{dataset.barCount.toLocaleString()} bars</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Symbols:</span>
              <span className="text-slate-800 dark:text-slate-200">{dataset.symbols.join(', ')}</span>
            </div>
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-1">
              <div className="text-slate-500 dark:text-slate-400 text-[10px]">Canonical Arrow Batch SHA-256:</div>
              <div className="text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/60 p-1.5 rounded truncate text-[10px] border border-slate-200 dark:border-slate-800">
                {dataset.canonicalBatchSha256}
              </div>
            </div>
          </div>
        </div>

        {/* Config Authority Proof */}
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-enterprise-border dark:border-slate-800 p-4 shadow-xs space-y-3 font-mono-code text-xs transition-colors">
          <div className="flex items-center space-x-2 border-b border-slate-100 dark:border-slate-800 pb-2">
            <FileCode className="w-4 h-4 text-slate-500 dark:text-slate-400" />
            <h4 className="font-semibold text-slate-900 dark:text-slate-100">Configuration Authority Contract</h4>
          </div>
          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Config Identifier:</span>
              <span className="text-slate-800 dark:text-slate-200">{config.configId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Execution Horizon:</span>
              <span className="text-slate-800 dark:text-slate-200">{config.executionModel.type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Friction Model:</span>
              <span className="text-slate-800 dark:text-slate-200">{config.frictionModel.totalFrictionBps} bps Total</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Parameters:</span>
              <span className="text-slate-800 dark:text-slate-200">lookback={config.parameters.lookbackBars}, deadband={config.parameters.deadbandBps}bps</span>
            </div>
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-1">
              <div className="text-slate-500 dark:text-slate-400 text-[10px]">Config SHA-256 Digest:</div>
              <div className="text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/60 p-1.5 rounded truncate text-[10px] border border-slate-200 dark:border-slate-800">
                {config.configHash}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
