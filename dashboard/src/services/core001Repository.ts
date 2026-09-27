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
  blockedResponse,
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
  /**
   * Fail-closed fetch semantics:
   * - HTTP 404 / genuinely absent snapshot -> EMPTY PRE-S1 (normal pre-Obs-#1).
   * - Any other non-OK status, network/read error, malformed JSON, wrong
   *   document, hypothesis/authority/capital violation -> BLOCKED.
   * Corruption is NEVER converted into a healthy-looking empty state.
   */
  async getState(): Promise<Core001ApiResponse> {
    const fetchedAtUtc = new Date().toISOString();
    let resp: Response;
    try {
      const base =
        typeof window !== 'undefined' && window.location
          ? `${window.location.pathname.replace(/\/[^/]*$/, '/')}`
          : '/';
      resp = await fetch(`${base}${SNAPSHOT_URL}`, {
        headers: { Accept: 'application/json' },
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return blockedResponse(`SNAPSHOT_UNREACHABLE: ${message}`, fetchedAtUtc);
    }
    if (!resp.ok) {
      if (resp.status === 404) {
        return {
          ok: true,
          data: buildEmptyPreS1State(fetchedAtUtc),
          error: null,
          fetchedAtUtc,
        };
      }
      return blockedResponse(`SNAPSHOT_HTTP_${resp.status}`, fetchedAtUtc);
    }
    let payload: unknown;
    try {
      payload = await resp.json();
    } catch {
      return blockedResponse('SNAPSHOT_MALFORMED_JSON', fetchedAtUtc);
    }
    try {
      const data = parseCore001Snapshot(payload, fetchedAtUtc);
      return { ok: true, data, error: null, fetchedAtUtc };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return blockedResponse(message, fetchedAtUtc);
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
