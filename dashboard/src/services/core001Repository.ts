/**
 * ACASH CORE-001 — Read-Only Data Repository
 *
 * Architecture (mirrors shadowRepository):
 * - Fetches the generated static snapshot (same-origin, no backend needed).
 * - Falls back to explicit EMPTY PRE-S1 state when no snapshot exists yet.
 * - READ-ONLY: GET/fetch only. No POST/PUT/PATCH/DELETE anywhere.
 * - No credentials handled. No order path exists. No systemctl/SSH.
 */

import { Core001ApiResponse } from '../types/core001';
import {
  buildEmptyPreS1State,
  parseCore001Snapshot,
} from './core001MockData';

const SNAPSHOT_URL = 'data/core001-status.json';
const POLL_INTERVAL_MS = 30_000; // 30 seconds, read-only refresh

export interface ICore001Repository {
  getState(): Promise<Core001ApiResponse>;
  subscribe(callback: (state: Core001ApiResponse) => void): () => void;
}

class SnapshotCore001Repository implements ICore001Repository {
  async getState(): Promise<Core001ApiResponse> {
    const fetchedAtUtc = new Date().toISOString();
    try {
      const base =
        typeof window !== 'undefined' && window.location
          ? `${window.location.pathname.replace(/\/[^/]*$/, '/')}`
          : '/';
      const resp = await fetch(`${base}${SNAPSHOT_URL}`, {
        headers: { Accept: 'application/json' },
      });
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const payload: unknown = await resp.json();
      const data = parseCore001Snapshot(payload, fetchedAtUtc);
      return { ok: true, data, error: null, fetchedAtUtc };
    } catch {
      // No snapshot yet (normal pre-first-observation): explicit PRE-S1.
      return {
        ok: true,
        data: buildEmptyPreS1State(fetchedAtUtc),
        error: null,
        fetchedAtUtc,
      };
    }
  }

  subscribe(callback: (state: Core001ApiResponse) => void): () => void {
    void this.getState().then(callback);
    const interval = setInterval(() => {
      void this.getState().then(callback);
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }
}

export const core001Repository: ICore001Repository = new SnapshotCore001Repository();
