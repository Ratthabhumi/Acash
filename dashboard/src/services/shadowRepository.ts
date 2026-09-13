/**
 * ACASH Shadow Tournament — Read-Only Data Repository
 *
 * Architecture:
 * - Polls /api/shadow/status when a live backend is available.
 * - Falls back to mock demo data with isMockData=true clearly set.
 * - READ-ONLY: zero mutation capability — dashboard never writes to runtime.
 * - No trading credentials handled. No order submission path exists.
 *
 * SHADOW / SIMULATED ONLY — NOT Paper — NOT Live — NOT HYP_003
 */

import { TournamentState, ShadowApiResponse } from '../types/shadow';
import { mockTournamentState } from './shadowMockData';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

// Live API base URL — configure via Vite env variable when backend exists.
// Default is same-origin relative path ('') which fetches /api/shadow/status.
const SHADOW_API_BASE = ((import.meta as unknown) as Record<string, unknown> & { env?: Record<string, string> }).env?.VITE_SHADOW_API_URL ?? '';

// Governance rule: Mock fallback is strictly disabled in production.
// Only enabled when explicitly set to 'true' in development/demo environments.
const SHADOW_ALLOW_MOCK = ((import.meta as unknown) as Record<string, unknown> & { env?: Record<string, string> }).env?.VITE_SHADOW_ALLOW_MOCK === 'true';

const POLL_INTERVAL_MS = 15_000; // 15 seconds

// ---------------------------------------------------------------------------
// Repository interface
// ---------------------------------------------------------------------------

export interface IShadowRepository {
  getState(): Promise<ShadowApiResponse<TournamentState>>;
  subscribe(
    callback: (state: ShadowApiResponse<TournamentState>) => void,
    onError?: (err: Error) => void
  ): () => void; // Returns unsubscribe function
}

// ---------------------------------------------------------------------------
// Implementation: Mock (no live API configured)
// ---------------------------------------------------------------------------

class MockShadowRepository implements IShadowRepository {
  async getState(): Promise<ShadowApiResponse<TournamentState>> {
    // Refresh the fetchedAt timestamp each call
    const state = {
      ...mockTournamentState,
      _meta: {
        ...mockTournamentState._meta,
        fetchedAtUtc: new Date().toISOString(),
      },
    };
    return {
      ok: true,
      data: state,
      error: null,
      fetchedAtUtc: new Date().toISOString(),
    };
  }

  subscribe(
    callback: (state: ShadowApiResponse<TournamentState>) => void,
  ): () => void {
    // Immediately fire once
    void this.getState().then(callback);

    const interval = setInterval(() => {
      void this.getState().then(callback);
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }
}

// ---------------------------------------------------------------------------
// Implementation: Live API (when VITE_SHADOW_API_URL is set)
// ---------------------------------------------------------------------------

/**
 * Path-prefix safe API endpoint resolver.
 *
 * Rules:
 * 1. If explicit baseUrl is provided, uses it (${baseUrl}/api/shadow/status).
 * 2. If running under a subpath like /acash/ (Tailscale route via Traefik), resolves to /acash/api/shadow/status.
 * 3. If running at domain root (LAN mew.lab or localhost), resolves to /api/shadow/status.
 */
export function getShadowApiEndpoint(baseUrl: string = SHADOW_API_BASE): string {
  if (baseUrl) {
    return `${baseUrl.replace(/\/$/, '')}/api/shadow/status`;
  }
  if (typeof window !== 'undefined' && window.location) {
    const pathname = window.location.pathname;
    const prefix = pathname.startsWith('/acash') ? '/acash' : '';
    return `${prefix}/api/shadow/status`;
  }
  return '/api/shadow/status';
}

class LiveShadowRepository implements IShadowRepository {
  private readonly baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  async getState(): Promise<ShadowApiResponse<TournamentState>> {
    const fetchedAt = new Date().toISOString();
    const endpoint = getShadowApiEndpoint(this.baseUrl);
    try {
      const resp = await fetch(endpoint, {
        headers: { Accept: 'application/json' },
        // No credentials, no auth headers — read-only public endpoint on private tailnet
      });

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status} ${resp.statusText}`);
      }

      const data: TournamentState = await resp.json() as TournamentState;
      return { ok: true, data, error: null, fetchedAtUtc: fetchedAt };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return {
        ok: false,
        data: null,
        error: `Shadow API unreachable: ${message}`,
        fetchedAtUtc: fetchedAt,
      };
    }
  }

  subscribe(
    callback: (state: ShadowApiResponse<TournamentState>) => void,
    onError?: (err: Error) => void,
  ): () => void {
    let active = true;

    const poll = async () => {
      if (!active) return;
      try {
        const result = await this.getState();
        if (active) callback(result);
      } catch (err) {
        if (active && onError) {
          onError(err instanceof Error ? err : new Error(String(err)));
        }
      }
    };

    void poll();
    const interval = setInterval(() => void poll(), POLL_INTERVAL_MS);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }
}

// ---------------------------------------------------------------------------
// Factory — resolves to live or mock based on environment
// ---------------------------------------------------------------------------

export function createShadowRepository(apiBase = SHADOW_API_BASE, allowMock = SHADOW_ALLOW_MOCK): IShadowRepository {
  // Fail-closed contract: Default is ALWAYS Live repository (same-origin /api/shadow/status).
  // Mock repository is permitted ONLY when VITE_SHADOW_ALLOW_MOCK=true is explicitly configured.
  if (allowMock) {
    return new MockShadowRepository();
  }
  return new LiveShadowRepository(apiBase);
}

export const shadowRepository: IShadowRepository = createShadowRepository();
