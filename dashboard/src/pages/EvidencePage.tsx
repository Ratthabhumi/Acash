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
      <div className="bg-surface rounded-lg border border-default p-4 shadow-xs transition-colors">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-semibold text-primary tracking-tight">
                Causal Evidence Lineage DAG
              </h2>
              <span className="text-xs font-mono-code px-2 py-0.5 rounded bg-surface-muted text-secondary font-medium">
                11 Canonical Stages
              </span>
            </div>
            <p className="text-xs text-secondary font-mono-code mt-0.5">
              Strict unidirectional causal progression from raw immutable ticks to final governance manifest
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <CopyablePill label="Final Manifest" value={metadata.manifestHash} truncateLength={10} />
          </div>
        </div>
      </div>

      {/* 2. Interactive 11-Stage Visual DAG Stepper */}
      <div className="bg-surface rounded-lg border border-default p-4 shadow-xs space-y-3 transition-colors">
        <div className="text-xs font-mono-code font-semibold text-secondary uppercase tracking-wider">
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
                    ? 'border-accent bg-accent text-white shadow-xs'
                    : 'border-default bg-surface hover:border-focus hover:bg-surface-muted text-primary'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`text-[10px] font-mono-code font-bold px-1.5 py-0.5 rounded ${
                      isSelected ? 'bg-surface text-primary' : 'bg-surface-muted text-secondary'
                    }`}
                  >
                    #{node.stageNumber}
                  </span>
                  {index < lineage.length - 1 && (
                    <ArrowRight className={`hidden xl:block w-3 h-3 ${isSelected ? 'text-white/70' : 'text-muted'} -mr-1`} />
                  )}
                </div>

                <div className="my-1">
                  <div className={`text-xs font-semibold leading-tight truncate ${isSelected ? 'text-white' : 'text-primary'}`}>
                    {node.stageName}
                  </div>
                  <div className={`text-[10px] font-mono-code truncate mt-0.5 ${isSelected ? 'text-white/80' : 'text-secondary'}`}>
                    {node.shortTitle}
                  </div>
                </div>

                <div className={`text-[9px] font-mono-code truncate ${isSelected ? 'text-white/70' : 'text-muted'}`}>
                  {node.artifactName}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Selected Stage Deep-Dive Inspection Panel */}
      {selectedNode && (
        <div className="bg-surface rounded-lg border border-default p-5 shadow-xs space-y-4 transition-colors">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-subtle pb-3">
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono-code text-xs font-bold px-2 py-0.5 rounded bg-accent text-white border border-accent-hover">
                  Stage {selectedNode.stageNumber} of 11
                </span>
                <h3 className="text-sm font-semibold text-primary">
                  {selectedNode.stageName}: {selectedNode.shortTitle}
                </h3>
              </div>
              <p className="text-xs text-secondary font-sans mt-1">
                {selectedNode.description}
              </p>
            </div>

            <CopyablePill label="Digest" value={selectedNode.hashOrDigest} truncateLength={14} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono-code text-xs">
            {/* Metadata Block 1 */}
            <div className="p-3 rounded bg-surface-muted border border-subtle space-y-1.5">
              <div className="text-[11px] text-muted">Authority Rule Contract</div>
              <div className="font-semibold text-primary text-xs truncate">
                {selectedNode.authorityRule}
              </div>
              <div className="text-[11px] text-muted pt-1">Python Source Module</div>
              <div className="text-secondary text-xs truncate">{selectedNode.sourceModule}</div>
            </div>

            {/* Metadata Block 2 */}
            <div className="p-3 rounded bg-surface-muted border border-subtle space-y-1.5">
              <div className="text-[11px] text-muted">Sealed Artifact</div>
              <div className="font-semibold text-primary text-xs truncate">
                {selectedNode.artifactName}
              </div>
              <div className="text-[11px] text-muted pt-1">Timestamp (UTC)</div>
              <div className="text-secondary text-xs truncate">{selectedNode.timestamp}</div>
            </div>

            {/* Metadata Block 3: Lineage Connections */}
            <div className="p-3 rounded bg-surface-muted border border-subtle space-y-1.5">
              <div className="text-[11px] text-muted">Upstream Origin</div>
              <div className="text-primary text-xs truncate">
                {selectedNode.inputLineage.join(', ') || 'Root Genesis'}
              </div>
              <div className="text-[11px] text-muted pt-1">Downstream Consumer</div>
              <div className="text-primary text-xs truncate">
                {selectedNode.outputLineage.join(', ') || 'Terminal Manifest'}
              </div>
            </div>
          </div>

          {/* Raw Structured Evidence Payload */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono-code text-secondary">
              <span className="font-semibold">Recorded Stage Evidence Payload (JSON)</span>
              <span className="text-[11px] text-muted">Cryptographically immutable state</span>
            </div>
            <pre className="p-3 rounded bg-[var(--code-bg)] text-[var(--code-text)] font-mono-code text-xs overflow-x-auto border border-[var(--code-border)]">
              {JSON.stringify(selectedNode.mockEvidencePayload, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* 4. Dataset & Configuration Cryptographic Proofs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dataset Origin Proof */}
        <div className="bg-surface rounded-lg border border-default p-4 shadow-xs space-y-3 font-mono-code text-xs transition-colors">
          <div className="flex items-center space-x-2 border-b border-subtle pb-2">
            <Database className="w-4 h-4 text-muted" />
            <h4 className="font-semibold text-primary">Dataset Lineage & Verification</h4>
          </div>
          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between">
              <span className="text-muted">Dataset ID:</span>
              <span className="text-primary">{dataset.datasetId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Storage Engine:</span>
              <span className="text-primary">{dataset.storageEngine}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Bar Count:</span>
              <span className="text-primary">{dataset.barCount.toLocaleString()} bars</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Symbols:</span>
              <span className="text-primary">{dataset.symbols.join(', ')}</span>
            </div>
            <div className="pt-2 border-t border-subtle space-y-1">
              <div className="text-muted text-[10px]">Canonical Arrow Batch SHA-256:</div>
              <div className="text-secondary bg-surface-muted p-1.5 rounded truncate text-[10px] border border-subtle">
                {dataset.canonicalBatchSha256}
              </div>
            </div>
          </div>
        </div>

        {/* Config Authority Proof */}
        <div className="bg-surface rounded-lg border border-default p-4 shadow-xs space-y-3 font-mono-code text-xs transition-colors">
          <div className="flex items-center space-x-2 border-b border-subtle pb-2">
            <FileCode className="w-4 h-4 text-muted" />
            <h4 className="font-semibold text-primary">Configuration Authority Contract</h4>
          </div>
          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between">
              <span className="text-muted">Config Identifier:</span>
              <span className="text-primary">{config.configId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Execution Horizon:</span>
              <span className="text-primary">{config.executionModel.type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Friction Model:</span>
              <span className="text-primary">{config.frictionModel.totalFrictionBps} bps Total</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Parameters:</span>
              <span className="text-primary">lookback={config.parameters.lookbackBars}, deadband={config.parameters.deadbandBps}bps</span>
            </div>
            <div className="pt-2 border-t border-subtle space-y-1">
              <div className="text-muted text-[10px]">Config SHA-256 Digest:</div>
              <div className="text-secondary bg-surface-muted p-1.5 rounded truncate text-[10px] border border-subtle">
                {config.configHash}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
