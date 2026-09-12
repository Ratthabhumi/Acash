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
      <div className="bg-white rounded-lg border border-enterprise-border p-4 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-semibold text-slate-900 tracking-tight">
                Causal Evidence Lineage DAG
              </h2>
              <span className="text-xs font-mono-code px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium">
                11 Canonical Stages
              </span>
            </div>
            <p className="text-xs text-slate-500 font-mono-code mt-0.5">
              Strict unidirectional causal progression from raw immutable ticks to final governance manifest
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <CopyablePill label="Final Manifest" value={metadata.manifestHash} truncateLength={10} />
          </div>
        </div>
      </div>

      {/* 2. Interactive 11-Stage Visual DAG Stepper */}
      <div className="bg-white rounded-lg border border-enterprise-border p-4 shadow-xs space-y-3">
        <div className="text-xs font-mono-code font-semibold text-slate-600 uppercase tracking-wider">
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
                    ? 'border-slate-900 bg-slate-900 text-white shadow-xs'
                    : 'border-slate-200 bg-white hover:border-slate-400 hover:bg-slate-50/80 text-slate-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`text-[10px] font-mono-code font-bold px-1.5 py-0.5 rounded ${
                      isSelected ? 'bg-slate-800 text-slate-200' : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    #{node.stageNumber}
                  </span>
                  {index < lineage.length - 1 && (
                    <ArrowRight className={`hidden xl:block w-3 h-3 ${isSelected ? 'text-slate-400' : 'text-slate-300'} -mr-1`} />
                  )}
                </div>

                <div className="my-1">
                  <div className={`text-xs font-semibold leading-tight truncate ${isSelected ? 'text-white' : 'text-slate-900'}`}>
                    {node.stageName}
                  </div>
                  <div className={`text-[10px] font-mono-code truncate mt-0.5 ${isSelected ? 'text-slate-300' : 'text-slate-500'}`}>
                    {node.shortTitle}
                  </div>
                </div>

                <div className={`text-[9px] font-mono-code truncate ${isSelected ? 'text-slate-400' : 'text-slate-400'}`}>
                  {node.artifactName}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Selected Stage Deep-Dive Inspection Panel */}
      {selectedNode && (
        <div className="bg-white rounded-lg border border-enterprise-border p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono-code text-xs font-bold px-2 py-0.5 rounded bg-slate-900 text-white">
                  Stage {selectedNode.stageNumber} of 11
                </span>
                <h3 className="text-sm font-semibold text-slate-900">
                  {selectedNode.stageName}: {selectedNode.shortTitle}
                </h3>
              </div>
              <p className="text-xs text-slate-600 font-sans mt-1">
                {selectedNode.description}
              </p>
            </div>

            <CopyablePill label="Digest" value={selectedNode.hashOrDigest} truncateLength={14} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono-code text-xs">
            {/* Metadata Block 1 */}
            <div className="p-3 rounded bg-slate-50 border border-slate-200 space-y-1.5">
              <div className="text-[11px] text-slate-500">Authority Rule Contract</div>
              <div className="font-semibold text-slate-900 text-xs truncate">
                {selectedNode.authorityRule}
              </div>
              <div className="text-[11px] text-slate-500 pt-1">Python Source Module</div>
              <div className="text-slate-700 text-xs truncate">{selectedNode.sourceModule}</div>
            </div>

            {/* Metadata Block 2 */}
            <div className="p-3 rounded bg-slate-50 border border-slate-200 space-y-1.5">
              <div className="text-[11px] text-slate-500">Sealed Artifact</div>
              <div className="font-semibold text-slate-900 text-xs truncate">
                {selectedNode.artifactName}
              </div>
              <div className="text-[11px] text-slate-500 pt-1">Timestamp (UTC)</div>
              <div className="text-slate-700 text-xs truncate">{selectedNode.timestamp}</div>
            </div>

            {/* Metadata Block 3: Lineage Connections */}
            <div className="p-3 rounded bg-slate-50 border border-slate-200 space-y-1.5">
              <div className="text-[11px] text-slate-500">Upstream Origin</div>
              <div className="text-slate-800 text-xs truncate">
                {selectedNode.inputLineage.join(', ') || 'Root Genesis'}
              </div>
              <div className="text-[11px] text-slate-500 pt-1">Downstream Consumer</div>
              <div className="text-slate-800 text-xs truncate">
                {selectedNode.outputLineage.join(', ') || 'Terminal Manifest'}
              </div>
            </div>
          </div>

          {/* Raw Structured Evidence Payload */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono-code text-slate-600">
              <span className="font-semibold">Recorded Stage Evidence Payload (JSON)</span>
              <span className="text-[11px] text-slate-400">Cryptographically immutable state</span>
            </div>
            <pre className="p-3 rounded bg-slate-900 text-slate-100 font-mono-code text-xs overflow-x-auto">
              {JSON.stringify(selectedNode.mockEvidencePayload, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* 4. Dataset & Configuration Cryptographic Proofs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dataset Origin Proof */}
        <div className="bg-white rounded-lg border border-enterprise-border p-4 shadow-xs space-y-3 font-mono-code text-xs">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
            <Database className="w-4 h-4 text-slate-500" />
            <h4 className="font-semibold text-slate-900">Dataset Lineage & Verification</h4>
          </div>
          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between">
              <span className="text-slate-500">Dataset ID:</span>
              <span className="text-slate-800">{dataset.datasetId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Storage Engine:</span>
              <span className="text-slate-800">{dataset.storageEngine}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Bar Count:</span>
              <span className="text-slate-800">{dataset.barCount.toLocaleString()} bars</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Symbols:</span>
              <span className="text-slate-800">{dataset.symbols.join(', ')}</span>
            </div>
            <div className="pt-2 border-t border-slate-100 space-y-1">
              <div className="text-slate-500 text-[10px]">Canonical Arrow Batch SHA-256:</div>
              <div className="text-slate-700 bg-slate-50 p-1.5 rounded truncate text-[10px]">
                {dataset.canonicalBatchSha256}
              </div>
            </div>
          </div>
        </div>

        {/* Config Authority Proof */}
        <div className="bg-white rounded-lg border border-enterprise-border p-4 shadow-xs space-y-3 font-mono-code text-xs">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
            <FileCode className="w-4 h-4 text-slate-500" />
            <h4 className="font-semibold text-slate-900">Configuration Authority Contract</h4>
          </div>
          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between">
              <span className="text-slate-500">Config Identifier:</span>
              <span className="text-slate-800">{config.configId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Execution Horizon:</span>
              <span className="text-slate-800">{config.executionModel.type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Friction Model:</span>
              <span className="text-slate-800">{config.frictionModel.totalFrictionBps} bps Total</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Parameters:</span>
              <span className="text-slate-800">lookback={config.parameters.lookbackBars}, deadband={config.parameters.deadbandBps}bps</span>
            </div>
            <div className="pt-2 border-t border-slate-100 space-y-1">
              <div className="text-slate-500 text-[10px]">Config SHA-256 Digest:</div>
              <div className="text-slate-700 bg-slate-50 p-1.5 rounded truncate text-[10px]">
                {config.configHash}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
